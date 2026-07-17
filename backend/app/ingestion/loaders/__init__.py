from collections.abc import Callable

from app.ingestion.loaders import csv, docx, html, markdown, pdf, source_code, text

LOADERS: dict[str, Callable[[bytes], str]] = {
    ".pdf": pdf.load,
    ".docx": docx.load,
    ".txt": text.load,
    ".md": markdown.load,
    ".html": html.load,
    ".htm": html.load,
    ".csv": csv.load,
    ".py": source_code.load,
    ".js": source_code.load,
    ".ts": source_code.load,
    ".java": source_code.load,
    ".cpp": source_code.load,
}


def load_document(extension: str, data: bytes) -> str:
    try:
        loader = LOADERS[extension.lower()]
    except KeyError as exc:
        raise ValueError(f"No loader registered for {extension}") from exc
    return loader(data)


__all__ = ["load_document"]
