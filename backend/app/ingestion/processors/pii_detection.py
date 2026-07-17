import re
from dataclasses import dataclass

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)")


@dataclass(frozen=True, slots=True)
class PIIFinding:
    kind: str
    start: int
    end: int


def find_pii(text: str) -> list[PIIFinding]:
    return [
        PIIFinding(kind, m.start(), m.end())
        for kind, pattern in (("email", EMAIL), ("phone", PHONE))
        for m in pattern.finditer(text)
    ]
