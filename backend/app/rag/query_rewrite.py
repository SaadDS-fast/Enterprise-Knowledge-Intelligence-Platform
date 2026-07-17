import re


def rewrite_query(query: str) -> str:
    query = re.sub(r"\s+", " ", query).strip()
    return query.rstrip("?") if len(query.split()) > 3 else query
