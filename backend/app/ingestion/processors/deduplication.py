from app.utils.hashing import hash_text


def deduplicate_chunks(chunks: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for chunk in chunks:
        digest = hash_text(chunk)
        if digest not in seen:
            seen.add(digest)
            result.append(chunk)
    return result
