from __future__ import annotations

import httpx

from app.security.ssrf import validate_outbound_url


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def get_file(self, owner: str, repo: str, path: str, ref: str = "main") -> dict:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        validate_outbound_url(url, {"api.github.com"})
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=self.headers, params={"ref": ref})
            response.raise_for_status()
            return response.json()
