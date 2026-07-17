def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def trim_to_budget(text: str, max_tokens: int) -> str:
    return text[: max_tokens * 4]
