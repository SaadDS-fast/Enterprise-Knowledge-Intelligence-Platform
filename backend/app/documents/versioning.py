def next_version_number(existing: list[int]) -> int:
    return max(existing, default=0) + 1
