from app.security.ssrf import validate_outbound_url

DEFAULT_ALLOWED_HOSTS = {"api.openai.com", "localhost", "127.0.0.1"}


def enforce_egress(url: str, allowed_hosts: set[str] | None = None) -> str:
    return validate_outbound_url(url, allowed_hosts or DEFAULT_ALLOWED_HOSTS)
