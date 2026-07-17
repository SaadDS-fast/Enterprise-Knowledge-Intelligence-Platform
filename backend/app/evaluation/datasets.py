import json
from pathlib import Path

from app.models.schemas import EvaluationCase


def load_jsonl(path: str | Path) -> list[EvaluationCase]:
    return [
        EvaluationCase.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
