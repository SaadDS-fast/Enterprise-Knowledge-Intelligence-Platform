from __future__ import annotations

import re

from app.core.config import settings

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    size = chunk_size or settings.chunk_size
    overlap = settings.chunk_overlap if overlap is None else overlap
    if not text.strip():
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= size:
            units.append(paragraph)
        else:
            units.extend(s.strip() for s in SENTENCE_BOUNDARY.split(paragraph) if s.strip())
    chunks: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > size:
            if current:
                chunks.append(current.strip())
                current = ""
            step = max(1, size - overlap)
            chunks.extend(
                unit[i : i + size].strip()
                for i in range(0, len(unit), step)
                if unit[i : i + size].strip()
            )
            continue
        candidate = f"{current} {unit}".strip()
        if len(candidate) <= size:
            current = candidate
        else:
            chunks.append(current.strip())
            tail = current[-overlap:].lstrip() if overlap and current else ""
            current = f"{tail} {unit}".strip()
    if current:
        chunks.append(current.strip())
    return chunks
