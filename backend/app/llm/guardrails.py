from app.security.prompt_security import scan_prompt


def validate_user_prompt(text: str) -> tuple[bool, tuple[str, ...]]:
    result = scan_prompt(text)
    return result.safe, result.matches
