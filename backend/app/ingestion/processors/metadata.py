from pathlib import Path


def build_metadata(filename: str, mime_type: str, size_bytes: int, text: str) -> dict:
    return {
        "filename": Path(filename).name,
        "extension": Path(filename).suffix.lower(),
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "character_count": len(text),
        "word_count": len(text.split()),
    }
