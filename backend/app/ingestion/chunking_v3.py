from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import settings
from app.ingestion.structure import BlockKind, ExtractedDocument, StructuralBlock


@dataclass(frozen=True, slots=True)
class StructuredChunk:
    content: str
    metadata: dict


def chunk_document(
    document: ExtractedDocument, *, chunk_size: int | None = None, overlap: int | None = None
) -> list[StructuredChunk]:
    size = chunk_size or settings.chunk_size
    overlap = min(settings.chunk_overlap if overlap is None else overlap, size // 5)
    chunks: list[StructuredChunk] = []
    active_heading: StructuralBlock | None = None
    pending: list[StructuralBlock] = []

    def flush() -> None:
        nonlocal pending
        if not pending:
            return
        content_blocks = (
            [active_heading] if active_heading and active_heading not in pending else []
        ) + pending
        content = "\n\n".join(
            block.text for block in content_blocks if block and block.text.strip()
        )
        for part in _bounded_parts(content, size, overlap):
            base = next((block for block in pending if block.text in part), pending[0])
            chunks.append(StructuredChunk(part, _metadata(base, active_heading, len(chunks))))
        pending = []

    for block in document.blocks:
        if not block.text.strip():
            continue
        if block.kind in {BlockKind.TITLE, BlockKind.HEADING}:
            flush()
            active_heading = block
            pending = [block]
            continue
        hard_boundary = block.kind in {BlockKind.QUESTION, BlockKind.TABLE, BlockKind.CODE}
        page_boundary = bool(
            pending and block.page and pending[-1].page and block.page != pending[-1].page
        )
        if hard_boundary or page_boundary:
            flush()
        candidate_length = sum(len(item.text) + 2 for item in pending) + len(block.text)
        if pending and candidate_length > size:
            flush()
        pending.append(block)
        if hard_boundary:
            flush()
    flush()
    return _quality_gate(chunks, size)


def _bounded_parts(content: str, size: int, overlap: int) -> list[str]:
    content = content.strip()
    if len(content) <= size:
        return [content] if content else []
    parts: list[str] = []
    cursor = 0
    while cursor < len(content):
        end = min(len(content), cursor + size)
        if end < len(content):
            boundary = max(
                content.rfind("\n", cursor + size // 2, end),
                content.rfind(" ", cursor + size // 2, end),
            )
            if boundary > cursor:
                end = boundary
        part = content[cursor:end].strip()
        if part:
            parts.append(part)
        cursor = max(end - overlap, cursor + 1)
        while (
            cursor < len(content)
            and cursor > 0
            and content[cursor - 1].isalnum()
            and content[cursor].isalnum()
        ):
            cursor += 1
    return parts


def _metadata(block: StructuralBlock, heading: StructuralBlock | None, ordinal: int) -> dict:
    return {
        "page": block.page,
        "section": block.section or (heading.section if heading else None),
        "heading": block.heading or (heading.heading if heading else None),
        "heading_level": block.heading_level or (heading.heading_level if heading else None),
        "question_number": block.question_number,
        "table_identifier": block.table_identifier,
        "row_range": block.row_range,
        "line_range": block.line_range,
        "chunk_order": ordinal,
        **block.metadata,
    }


def _quality_gate(chunks: list[StructuredChunk], size: int) -> list[StructuredChunk]:
    accepted: list[StructuredChunk] = []
    seen: set[str] = set()
    for chunk in chunks:
        normalized = re.sub(r"\s+", " ", chunk.content).strip()
        key = normalized.casefold()
        printable = (
            sum(char.isprintable() for char in normalized) / len(normalized) if normalized else 0
        )
        has_context = any(
            chunk.metadata.get(key)
            for key in ("heading", "section", "question_number", "table_identifier", "line_range")
        )
        if (
            not normalized
            or key in seen
            or len(normalized) > size
            or printable < 0.75
            or (len(normalized) < 20 and not has_context)
            or (normalized[-1:].isalnum() and len(normalized) == size)
        ):
            continue
        seen.add(key)
        accepted.append(chunk)
    return accepted
