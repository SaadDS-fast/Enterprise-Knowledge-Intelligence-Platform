from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BlockKind(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    QUESTION = "question"
    TABLE = "table"
    CODE = "code"
    CAPTION = "caption"
    PAGE_BREAK = "page_break"


@dataclass(slots=True)
class StructuralBlock:
    text: str
    kind: BlockKind = BlockKind.PARAGRAPH
    page: int | None = None
    heading: str | None = None
    heading_level: int | None = None
    section: str | None = None
    question_number: str | None = None
    table_identifier: str | None = None
    row_range: str | None = None
    line_range: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedDocument:
    blocks: list[StructuralBlock]
    page_count: int | None = None
    empty_pages: int = 0
    scanned_likelihood: float = 0.0
    reading_order_warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text.strip()).strip()
