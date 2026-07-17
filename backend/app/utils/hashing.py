import hashlib


def hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_text(value: str) -> str:
    return hash_bytes(value.encode("utf-8"))


def hash_ip(value: str, salt: str) -> str:
    return hash_text(f"{salt}:{value}")
