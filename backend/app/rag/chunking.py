from __future__ import annotations

import re

from app.core.config import settings

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
HEADING_VALUE = re.compile(r"^\s*(?:#{1,6}\s*)?[A-Za-z][A-Za-z0-9 &/-]{1,80}\s*[:=-]\s*\S")
MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+\S")
CONTEXT_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:section|topic|chapter|unit|subject)\s*[:=-]\s*\S", re.I
)
QUESTION_START = re.compile(r"^\s*(?:question|q)\s*\d+[A-Za-z]?\s*[:.)-]\s*\S", re.I)


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    size = chunk_size or settings.chunk_size
    overlap = settings.chunk_overlap if overlap is None else overlap
    if not text.strip():
        return []
    paragraphs = _structural_units(text)
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= size:
            units.append(paragraph)
        else:
            units.extend(s.strip() for s in SENTENCE_BOUNDARY.split(paragraph) if s.strip())
    chunks: list[str] = []
    current = ""
    for unit in units:
        if HEADING_VALUE.match(unit):
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(unit.strip())
            continue
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


def _structural_units(text: str) -> list[str]:
    units: list[str] = []
    current: list[str] = []
    current_has_question = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                units.append("\n".join(current).strip())
                current = []
                current_has_question = False
            continue
        is_context_heading = bool(CONTEXT_HEADING.match(line))
        is_question = bool(QUESTION_START.match(line))
        if is_context_heading and current:
            units.append("\n".join(current).strip())
            current = []
            current_has_question = False
        if is_question and current_has_question:
            units.append("\n".join(current).strip())
            carried_heading = _last_context_heading(current)
            current = [carried_heading] if carried_heading else []
            current_has_question = False
        starts_new = bool(HEADING_VALUE.match(line) or MARKDOWN_HEADING.match(line))
        if starts_new and not is_context_heading and not is_question and current:
            units.append("\n".join(current).strip())
            current = []
            current_has_question = False
        current.append(line)
        current_has_question = current_has_question or is_question
        if HEADING_VALUE.match(line) and not is_context_heading and not is_question:
            units.append("\n".join(current).strip())
            current = []
            current_has_question = False
    if current:
        units.append("\n".join(current).strip())
    return [unit for unit in units if unit]


def _last_context_heading(lines: list[str]) -> str | None:
    for line in reversed(lines):
        if CONTEXT_HEADING.match(line):
            return line
    return None
