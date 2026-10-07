from __future__ import annotations

from recondeck.models import Finding


def _finding(rule_id: str, flag: str, stage: int, title: str, evidence, why: str, fix: str = "", refs=None):
    refs = refs or []
    return Finding(id=rule_id, flag=flag, stage=stage, title=title, evidence=list(evidence), why=why, fix=fix, refs=refs)


def rule_whois_001(data):
    whois = data.get("whois", {})
    text = (whois.get("stdout") or "") + (whois.get("stderr") or "")
    if not text:
        return [_finding("WHOIS-004", "grey", 7, "Whois failed", ["No readable whois output found"], "Whois did not return a usable registration record.", "Check the domain registration server and retry the whois lookup.")]
    lower = text.lower()
    if "expires:" in lower or "renewal:" in lower or "expiration:" in lower:
        for token in ("expires:", "renewal:", "expiration:"):
            pos = lower.find(token)
            if pos != -1:
                chunk = text[pos + len(token): pos + len(token) + 80]
                return [_finding("WHOIS-001", "green", 7, "Domain expiry looks healthy", [chunk.strip()], "The whois information exposes a renewal date that is not immediately near expiry.", "")]
    return [_finding("WHOIS-001", "green", 7, "Registration age is acceptable", ["whois data present"], "The whois record was available and did not indicate an imminent expiry.", "")]


def rule_whois_002(data):
    whois = data.get("whois", {})
    text = (whois.get("stdout") or "") + (whois.get("stderr") or "")
    if not text:
        return []
    lower = text.lower()
    if all(token not in lower for token in ("transfer lock", "registrar lock", "delete lock", "domain lock")):
        return [_finding("WHOIS-002", "yellow", 7, "No transfer or delete lock status visible", ["whois output did not show lock status"], "The domain registration data does not show a transfer or delete lock in the standard fields.", "Add a lock or verify registry protections.")]
    return []


def rule_whois_003(data):
    whois = data.get("whois", {})
    text = (whois.get("stdout") or "") + (whois.get("stderr") or "")
    if not text:
        return []
    lower = text.lower()
    if "created:" in lower or "registered:" in lower:
        return [_finding("WHOIS-003", "yellow", 7, "Domain age is recent", ["Created date noted in whois output"], "The domain was registered recently enough that extra scrutiny may still be useful.", "")]
    return []


def rule_whois_004(data):
    whois = data.get("whois", {})
    if not whois or not ((whois.get("stdout") or "") + (whois.get("stderr") or "")):
        return [_finding("WHOIS-004", "grey", 7, "Whois failed", ["No usable output"], "Whois data was unavailable, so the registration status is unknown.", "Retry whois lookups or use a different registry view.")]
    return []
