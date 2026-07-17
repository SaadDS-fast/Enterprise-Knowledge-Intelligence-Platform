import re

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)")
API_KEY = re.compile(r"\b(?:sk|api)[-_][A-Za-z0-9_-]{16,}\b", re.I)


def redact_text(text: str) -> str:
    text = API_KEY.sub("[REDACTED_API_KEY]", text)
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    return PHONE.sub("[REDACTED_PHONE]", text)


def safe_log_fields(fields: dict) -> dict:
    return {
        key: redact_text(str(value)) if isinstance(value, str) else value
        for key, value in fields.items()
        if key.lower() not in {"password", "token", "secret", "authorization"}
    }
