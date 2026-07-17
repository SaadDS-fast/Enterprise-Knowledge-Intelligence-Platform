def detect_regression(current: float, baseline: float, tolerance: float = 0.02) -> bool:
    return current < baseline - tolerance
