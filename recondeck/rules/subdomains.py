from __future__ import annotations

from recondeck.models import Finding


def _finding(rule_id: str, flag: str, stage: int, title: str, evidence, why: str, fix: str = "", refs=None):
    refs = refs or []
    return Finding(id=rule_id, flag=flag, stage=stage, title=title, evidence=list(evidence), why=why, fix=fix, refs=refs)


def rule_sub_001(data):
    subdomains = data.get("subdomains", {})
    if isinstance(subdomains, dict) and subdomains:
        names = list(subdomains.keys())[:5]
        return [_finding("SUB-001", "green", 5, "Subdomains discovered", [f"{len(subdomains)} names found", *names], "Passively discovered names were gathered from DNS and certificate sources.", "")]
    return []


def rule_sub_002(data):
    interesting = data.get("interesting_names", [])
    if interesting:
        return [_finding("SUB-002", "yellow", 5, "Interesting names were discovered", interesting[:10], "Some names match common internal or operational labels, which often indicate staging or internal services.", "Review those names to confirm whether they are intentional and properly exposed.")]
    return []


def rule_sub_003(data):
    ips = data.get("ips", {})
    private = []
    for ip, info in ips.items():
        if ip.startswith(("10.", "192.168.", "172.16.", "127.", "169.254.")):
            private.append(ip)
    if private:
        return [_finding("SUB-003", "yellow", 5, "Private or reserved IPs are present", private[:5], "At least one host resolves to a private or reserved address, which can indicate internal infrastructure.", "Validate whether the service should be publicly reachable and whether it should be filtered out.")]
    return []


def rule_sub_004(data):
    subdomains = data.get("subdomains", {})
    dangling = []
    for name, info in subdomains.items():
        if info.get("status") == "dangling":
            dangling.append(name)
    if dangling:
        return [_finding("SUB-004", "red", 5, "Dangling CNAME found", dangling[:5], "A CNAME target appears to have no valid record, which may create a subdomain takeover opportunity.", "Claim the target resource or remove the stale CNAME.")]
    return []


def rule_sub_005(data):
    subdomains = data.get("subdomains", {})
    takeover = []
    for name, info in subdomains.items():
        if info.get("provider"):
            takeover.append(f"{name}: {info['provider']}")
    if takeover:
        return [_finding("SUB-005", "yellow", 5, "Takeover-prone providers appear in subdomains", takeover[:5], "Some discovered names point at a provider or service commonly associated with takeover risk.", "Verify the resource is actually claimed and configured.")]
    return []


def rule_sub_006(data):
    cert = data.get("certificates", [])
    if cert:
        return [_finding("SUB-006", "yellow", 5, "Names appear in certificate logs but not DNS", cert[:5], "Certificate transparency data includes names that are not present in DNS, which can reveal internal or historical names.", "Review whether the names are still in use or should be retired.")]
    return []


def rule_sub_007(data):
    cert = data.get("certificates", [])
    if cert and not data.get("subdomains"):
        return [_finding("SUB-007", "green", 5, "Certificate-only names were observed", cert[:5], "Names seen only in certificates can still be meaningful as historical or internal naming evidence.", "")]
    return []


def rule_ip_001(data):
    ips = data.get("ips", {})
    if ips:
        owners = sorted({info.get("owner", "unknown") for info in ips.values()})
        return [_finding("IP-001", "green", 7, "Hosting footprint summary", [f"{len(ips)} IP(s) across {len(owners)} owners", *owners[:5]], "The detected IPs map to the hosting and ownership context that helps explain the service footprint.", "")]
    return []


def rule_ip_002(data):
    ips = data.get("ips", {})
    matches = []
    for ip, info in ips.items():
        ptr = info.get("ptr", [])
        for value in ptr:
            lower = value.lower()
            if any(token in lower for token in ["internal", "mail", "vpn", "corp", "db", "admin", "staging", "prod"]):
                matches.append(f"{ip}: {value}")
    if matches:
        return [_finding("IP-002", "yellow", 7, "Reverse DNS exposes internal-looking names", matches[:5], "Some reverse-DNS names look internal or operational rather than public-facing, which can reveal internal infrastructure.", "Review whether the PTR records should be restricted or cleaned up.")]
    return []
