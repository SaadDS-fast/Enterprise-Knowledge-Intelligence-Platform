import re

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
MULTI_SPACE = re.compile(r"[ \t]+")
MULTI_NEWLINE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = ZERO_WIDTH.sub("", text)
    text = "\n".join(MULTI_SPACE.sub(" ", line).strip() for line in text.splitlines())
    return MULTI_NEWLINE.sub("\n\n", text).strip()
