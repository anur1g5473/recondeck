import secrets
from urllib.parse import urlparse

from . import config


def set_app_token(token: str) -> str:
    config.APP_TOKEN = token or ""
    return config.APP_TOKEN


def ensure_valid_token(token: str) -> bool:
    if not token or not config.APP_TOKEN:
        return False
    return secrets.compare_digest(token, config.APP_TOKEN)


def host_allowed(host_value: str, port: int) -> bool:
    if not host_value:
        return False
    value = host_value.strip().rstrip("/")
    if not value:
        return False

    if value.startswith("[") and "]" in value:
        host_part, sep, port_part = value.rpartition("]")
        if not sep:
            return False
        host = host_part[1:]
        if not port_part.startswith(":"):
            return False
        port_text = port_part[1:]
    else:
        if ":" not in value:
            return False
        host, sep, port_text = value.rpartition(":")
        if not sep:
            return False

    host = host.lower()
    if host not in {"127.0.0.1", "localhost"}:
        return False
    if not port_text or not port_text.isdigit():
        return False
    return True


def origin_allowed(origin_value: str, port: int) -> bool:
    if not origin_value:
        return True
    parsed = urlparse(origin_value)
    if parsed.scheme != "http":
        return False
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in {"127.0.0.1", "localhost"}:
        return False
    if parsed.port is None:
        return False
    return True
