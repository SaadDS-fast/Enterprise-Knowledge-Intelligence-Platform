import re


def rewrite_query(query: str) -> str:
    query = re.sub(r"\s+", " ", query).strip().rstrip("?")
    normalized = query.lower()
    if normalized in {"demo topic", "topic", "what topic", "what is this demo about"}:
        return "demo topic"
    if "demo" in normalized and "about" in normalized:
        return f"{query} topic subject covered"
    if "topic" in normalized:
        return f"{query} subject covered"
    return query
