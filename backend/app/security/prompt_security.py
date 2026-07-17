from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS = [
    re.compile(r"ignore\s+(all|any|the)\s+(previous|prior|system)\s+instructions", re.I),
    re.compile(r"reveal\s+(the\s+)?(system|developer)\s+prompt", re.I),
    re.compile(r"exfiltrat(e|ion)|send\s+.*\s+to\s+https?://", re.I),
    re.compile(r"bypass\s+(security|authorization|permissions)", re.I),
]


@dataclass(frozen=True, slots=True)
class PromptScan:
    safe: bool
    matches: tuple[str, ...]


def scan_prompt(text: str) -> PromptScan:
    matches = tuple(pattern.pattern for pattern in PATTERNS if pattern.search(text))
    return PromptScan(not matches, matches)


def wrap_untrusted_evidence(text: str) -> str:
    return f"<untrusted_document_content>\n{text}\n</untrusted_document_content>"
