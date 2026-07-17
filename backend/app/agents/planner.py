def build_plan(question: str) -> list[str]:
    return [
        "Normalize the question",
        "Retrieve workspace evidence",
        "Verify evidence sufficiency",
        "Draft a cited answer",
        "Run safety review",
    ]
