import io

from pypdf import PdfReader


def load(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(
        (page.extract_text() or "").strip() for page in reader.pages if page.extract_text()
    )
