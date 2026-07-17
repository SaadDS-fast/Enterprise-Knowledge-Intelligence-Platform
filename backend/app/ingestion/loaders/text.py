def load(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")
