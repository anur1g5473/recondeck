import ipaddress
import re
import tldextract

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+([a-z]{2,63}|xn--[a-z0-9-]+)$"
)


def is_valid_hostname(value: str) -> bool:
    return isinstance(value, str) and bool(_HOSTNAME_RE.fullmatch(value))


def parse_target(value: str) -> dict:
    if not isinstance(value, str):
        raise ValueError("Target must be a string.")

    candidate = value.strip()
    if not candidate or len(candidate) > 300:
        raise ValueError("Target must be between 1 and 300 characters.")

    if "://" in candidate:
        candidate = candidate.split("://", 1)[1]
    candidate = candidate.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    candidate = candidate.rsplit("@", 1)[-1]

    if ":" in candidate and candidate.rsplit(":", 1)[1].isdigit():
        candidate = candidate.rsplit(":", 1)[0]

    candidate = candidate.lower().rstrip(".")
    if not candidate:
        raise ValueError("Target is empty after parsing.")

    try:
        candidate = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Target is not valid IDNA.") from exc

    if candidate.startswith("-") or any(ch in candidate for ch in [" ", ";", "|", "&", "`", "$"]):
        raise ValueError("Target contains invalid characters.")

    if candidate == "localhost" or candidate.endswith(".local") or candidate.endswith(".internal") or candidate.endswith(".lan") or candidate.endswith(".home.arpa"):
        raise ValueError("Local or private names are not allowed.")

    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses are not allowed.")

    if not is_valid_hostname(candidate):
        raise ValueError("Target is not a valid hostname.")

    extractor = tldextract.TLDExtract(suffix_list_urls=())
    extracted = extractor(candidate)
    registered_domain = extracted.registered_domain or candidate
    if not registered_domain:
        raise ValueError("Could not determine a registered domain.")

    return {"hostname": candidate, "registered_domain": registered_domain, "suffix": extracted.suffix or ""}
