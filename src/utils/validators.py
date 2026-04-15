"""Input data validation utilities."""

from urllib.parse import urlparse


def is_valid_url(url: str, allowed_domain: str = "bemol.com.br") -> bool:
    """Validates if a string is a well-formed HTTP/HTTPS URL and matches the domain."""
    try:
        result = urlparse(url.strip())
        is_allowed = result.netloc == allowed_domain or result.netloc.endswith(f".{allowed_domain}")
        return all([result.scheme in ("http", "https"), is_allowed])
    except (ValueError, AttributeError):
        return False
