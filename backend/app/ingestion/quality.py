from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum

from app.ingestion.structure import BlockKind, ExtractedDocument


class ExtractionQuality(StrEnum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    LOW_QUALITY = "LOW_QUALITY"
    REQUIRES_OCR = "REQUIRES_OCR"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    status: ExtractionQuality
    extracted_character_count: int
    printable_character_ratio: float
    replacement_character_count: int
    duplicate_line_ratio: float
    empty_page_count: int
    page_coverage: float
    suspicious_token_fragmentation: float
    average_line_length: float
    equation_symbol_count: int
    table_count: int
    scanned_document_likelihood: float
    reading_order_warnings: tuple[str, ...]

    def as_dict(self) -> dict:
        value = asdict(self)
        value["status"] = self.status.value
        return value


def assess_extraction(document: ExtractedDocument) -> QualityAssessment:
    text = document.text
    characters = len(text)
    printable = sum(char.isprintable() or char in "\n\t" for char in text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    unique_lines = {line.casefold() for line in lines}
    duplicate_ratio = 1 - (len(unique_lines) / len(lines)) if lines else 0.0
    page_count = document.page_count or 0
    coverage = (
        max(0.0, (page_count - document.empty_pages) / page_count)
        if page_count
        else (1.0 if text else 0.0)
    )
    tokens = text.split()
    fragmented = sum(bool(re.fullmatch(r"[^A-Za-z0-9\s]{3,}|[A-Za-z]", token)) for token in tokens)
    fragmentation = fragmented / len(tokens) if tokens else 0.0
    replacement_count = text.count("\ufffd")
    printable_ratio = printable / characters if characters else 0.0
    scanned = max(0.0, min(1.0, document.scanned_likelihood))
    if scanned >= 0.8 and characters < 100:
        status = ExtractionQuality.REQUIRES_OCR
    elif not text:
        status = ExtractionQuality.FAILED
    elif printable_ratio < 0.75 or replacement_count > max(10, characters * 0.02):
        status = ExtractionQuality.LOW_QUALITY
    elif coverage < 0.6 or duplicate_ratio > 0.35 or fragmentation > 0.18:
        status = ExtractionQuality.LOW_QUALITY
    elif document.reading_order_warnings or printable_ratio < 0.95 or coverage < 0.9:
        status = ExtractionQuality.ACCEPTABLE
    else:
        status = ExtractionQuality.GOOD
    return QualityAssessment(
        status=status,
        extracted_character_count=characters,
        printable_character_ratio=round(printable_ratio, 4),
        replacement_character_count=replacement_count,
        duplicate_line_ratio=round(duplicate_ratio, 4),
        empty_page_count=document.empty_pages,
        page_coverage=round(coverage, 4),
        suspicious_token_fragmentation=round(fragmentation, 4),
        average_line_length=round(sum(map(len, lines)) / len(lines), 2) if lines else 0.0,
        equation_symbol_count=sum(text.count(char) for char in "=±×÷√∑∫²³≤≥≠"),
        table_count=sum(block.kind == BlockKind.TABLE for block in document.blocks),
        scanned_document_likelihood=round(scanned, 4),
        reading_order_warnings=tuple(document.reading_order_warnings),
    )
