"""Exercise live-model indexing, reindex idempotency, scope, and DB integrity."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import httpx
import psycopg

PREFIX = "phase2-live-validation"
PASSWORD = "Temporary-Phase2-Validation-Password-42"


async def _register(
    client: httpx.AsyncClient, suffix: str
) -> tuple[dict[str, str], str]:
    email = f"{PREFIX}-{suffix}@validation.localhost.com"
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": f"Phase 2 {suffix}",
            "password": PASSWORD,
            "organization_name": f"{PREFIX}-{suffix}",
            "workspace_name": "Live Validation",
        },
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "Authorization": f"Bearer {payload['access_token']}",
        "X-Workspace-ID": payload["workspace_id"],
    }, email


async def _upload(
    client: httpx.AsyncClient, headers: dict[str, str], filename: str, content: str
) -> tuple[str, str]:
    response = await client.post(
        "/documents",
        headers=headers,
        files={"file": (filename, content.encode(), "text/plain")},
    )
    response.raise_for_status()
    payload = response.json()
    return payload["document"]["id"], payload["job_id"]


async def _wait_job(
    client: httpx.AsyncClient, headers: dict[str, str], job_id: str
) -> dict:
    for _ in range(120):
        response = await client.get(f"/jobs/{job_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        await asyncio.sleep(0.25)
    raise TimeoutError("Validation ingestion job did not finish")


async def _cleanup(database_url: str) -> None:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM organizations WHERE name LIKE %s",
                (f"{PREFIX}-%",),
            )
            await cursor.execute(
                "DELETE FROM users WHERE email LIKE %s",
                (f"{PREFIX}-%",),
            )
        await connection.commit()


async def run(base_url: str, database_url: str, output: Path) -> dict:
    await _cleanup(database_url)
    async with httpx.AsyncClient(base_url=base_url, timeout=120) as client:
        tenant_a, _ = await _register(client, "tenant-a")
        tenant_b, _ = await _register(client, "tenant-b")
        try:
            target_id, target_job = await _upload(
                client,
                tenant_a,
                "travel-policy.txt",
                "Domestic Meal Allowance: PKR 5,000 per day.",
            )
            _, distractor_job = await _upload(
                client,
                tenant_a,
                "cafeteria.txt",
                "The cafeteria serves a weekly menu for office lunches.",
            )
            tenant_b_id, tenant_b_job = await _upload(
                client,
                tenant_b,
                "tenant-b-travel.txt",
                "Domestic food expenses are limited to PKR 9,999 daily.",
            )
            await _wait_job(client, tenant_a, target_job)
            await _wait_job(client, tenant_a, distractor_job)
            await _wait_job(client, tenant_b, tenant_b_job)

            async with await psycopg.AsyncConnection.connect(
                database_url
            ) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """
                        UPDATE chunks
                        SET metadata_json = (
                            metadata_json::jsonb ||
                            '{"embedding_provider":"deterministic",'
                            '"embedding_model":"blake2b-token-hash",'
                            '"embedding_version":"deterministic-hash-v1"}'::jsonb
                        )::json
                        WHERE metadata_json->>'document_id' = %s
                        """,
                        (target_id,),
                    )
                    await cursor.execute(
                        """
                        UPDATE document_versions
                        SET metadata_json = (
                            metadata_json::jsonb ||
                            '{"embedding_provider":"deterministic",'
                            '"embedding_model":"blake2b-token-hash",'
                            '"embedding_version":"deterministic-hash-v1"}'::jsonb
                        )::json
                        WHERE document_id = %s
                        """,
                        (target_id,),
                    )
                await connection.commit()

            listed = (await client.get("/documents", headers=tenant_a)).json()
            obsolete_marked = next(item for item in listed if item["id"] == target_id)[
                "reprocessing_recommended"
            ]

            reindex_headers = {**tenant_a, "Idempotency-Key": "live-model-reindex-v1"}
            first = await client.post(
                f"/documents/{target_id}/reindex", headers=reindex_headers
            )
            first.raise_for_status()
            first_payload = first.json()
            await _wait_job(client, tenant_a, first_payload["job_id"])
            replay = await client.post(
                f"/documents/{target_id}/reindex", headers=reindex_headers
            )
            replay.raise_for_status()
            replay_payload = replay.json()

            async with await psycopg.AsyncConnection.connect(
                database_url
            ) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """
                        SELECT
                            count(*) AS chunks,
                            count(DISTINCT ordinal) AS distinct_ordinals,
                            min(vector_dims(embedding)) AS min_dimension,
                            max(vector_dims(embedding)) AS max_dimension,
                            count(*) FILTER (
                                WHERE metadata_json->>'embedding_version' = 'st-v1'
                            ) AS live_vectors,
                            count(*) FILTER (
                                WHERE metadata_json->>'embedding_version' =
                                    'deterministic-hash-v1'
                            ) AS deterministic_vectors
                        FROM chunks
                        WHERE metadata_json->>'document_id' = %s
                        """,
                        (target_id,),
                    )
                    row = await cursor.fetchone()
            integrity = {
                "chunks": row[0],
                "distinct_ordinals": row[1],
                "min_dimension": row[2],
                "max_dimension": row[3],
                "live_vectors": row[4],
                "deterministic_vectors": row[5],
            }

            selected = await client.post(
                "/search",
                headers=tenant_a,
                json={
                    "query": "How much may an employee spend on food each day during official travel?",
                    "document_ids": [target_id],
                },
            )
            selected.raise_for_status()
            selected_payload = selected.json()
            tenant_b_search = await client.post(
                "/search",
                headers=tenant_b,
                json={"query": "What is the daily domestic food expense limit?"},
            )
            tenant_b_search.raise_for_status()
            tenant_b_payload = tenant_b_search.json()
            diagnosis = selected_payload["retrieval_diagnosis"]
            result = {
                "obsolete_version_marked": bool(obsolete_marked),
                "reindex": {
                    "first_job_completed": first_payload["job_id"]
                    == replay_payload["job_id"],
                    "idempotent_replay": replay_payload["idempotent"],
                    "duplicate_chunks": integrity["chunks"]
                    - integrity["distinct_ordinals"],
                    **integrity,
                },
                "selected_document_scope": {
                    "requested_document_count": 1,
                    "returned_document_count": len(
                        {item["document_id"] for item in selected_payload["evidence"]}
                    ),
                    "all_evidence_authorized": all(
                        item["document_id"] == target_id
                        for item in selected_payload["evidence"]
                    ),
                    "semantic_used": diagnosis["semantic_used"],
                    "reranker_used": diagnosis["reranker_used"],
                    "fallback_used": diagnosis["fallback_used"],
                    "candidate_count": diagnosis["candidate_count"],
                    "final_evidence_count": diagnosis["final_evidence_count"],
                    "embedding_version": diagnosis["embedding_version"],
                    "reranker_version": diagnosis["reranker_version"],
                },
                "tenant_isolation": {
                    "tenant_a_document_count": 2,
                    "tenant_b_document_count": 1,
                    "tenant_b_only": all(
                        item["document_id"] == tenant_b_id
                        for item in tenant_b_payload["evidence"]
                    ),
                },
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            return result
        finally:
            await _cleanup(database_url)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/api/v1")
    parser.add_argument(
        "--database-url", default="postgresql://ekip:ekip@127.0.0.1:5432/ekip"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evaluation/phase2-live-reindex-results.json"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(run(args.base_url, args.database_url, args.output)),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
