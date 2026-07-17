from __future__ import annotations

import hashlib
import math
import re

from app.core.config import settings

TOKEN = re.compile(r"[\w'-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN.findall(text)]


def embed_text(text: str, dimension: int | None = None) -> list[float]:
    dimension = dimension or settings.embedding_dimension
    vector = [0.0] * dimension
    tokens = tokenize(text)
    for token in tokens:
        digest = hashlib.blake2b(token.encode(), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "big") % dimension
        sign = 1.0 if digest[8] & 1 else -1.0
        vector[index] += sign * (1.0 + math.log1p(len(token)))
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True))))
