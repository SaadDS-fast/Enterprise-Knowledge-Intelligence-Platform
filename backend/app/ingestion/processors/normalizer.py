import re
import unicodedata

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
MULTI_SPACE = re.compile(r"[ \t]+")
MULTI_NEWLINE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = ZERO_WIDTH.sub("", text)
    # Preserve code/list indentation and mathematical symbols. Only trim trailing space.
    text = "\n".join(MULTI_SPACE.sub(" ", line).rstrip() for line in text.splitlines())
    return MULTI_NEWLINE.sub("\n\n", text).strip()


def remove_repeated_page_furniture(pages: list[str]) -> list[str]:
    """Remove only lines repeated at the same edge on at least 60% of 3+ pages."""
    if len(pages) < 3:
        return pages
    edge_counts: dict[str, int] = {}
    page_lines = [page.splitlines() for page in pages]
    for lines in page_lines:
        for line in {item.strip() for item in (lines[:2] + lines[-2:]) if item.strip()}:
            edge_counts[line] = edge_counts.get(line, 0) + 1
    repeated = {line for line, count in edge_counts.items() if count / len(pages) >= 0.6}
    return [
        "\n".join(line for line in lines if line.strip() not in repeated) for lines in page_lines
    ]
