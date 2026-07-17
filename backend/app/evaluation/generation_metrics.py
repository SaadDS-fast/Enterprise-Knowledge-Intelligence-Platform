import re
from collections import Counter


def normalize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def exact_match(prediction: str, reference: str) -> float:
    return float(" ".join(normalize(prediction)) == " ".join(normalize(reference)))


def token_f1(prediction: str, reference: str) -> float:
    p, r = normalize(prediction), normalize(reference)
    if not p or not r:
        return float(p == r)
    common = sum((Counter(p) & Counter(r)).values())
    if not common:
        return 0.0
    precision, recall = common / len(p), common / len(r)
    return 2 * precision * recall / (precision + recall)
