from app.security.prompt_security import scan_prompt


def review(text: str) -> tuple[bool, tuple[str, ...]]:
    result = scan_prompt(text)
    return result.safe, result.matches
