from tenacity import retry, stop_after_attempt, wait_exponential


def resilient(attempts: int = 3):
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
