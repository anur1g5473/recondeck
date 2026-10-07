from __future__ import annotations

import re

from recondeck.models import Finding


def _finding(rule_id: str, flag: str, stage: int, title: str, evidence, why: str, fix: str = "", refs=None):
    refs = refs or []
    return Finding(id=rule_id, flag=flag, stage=stage, title=title, evidence=list(evidence), why=why, fix=fix, refs=refs)


def _text_records(data):
    host = data.get("target", {}).get("hostname")
    values = []
    for resolver_data in data.get("records", {}).values():
        if not isinstance(resolver_data, dict):
            continue
        if host:
            host_data = resolver_data.get(host)
            if isinstance(host_data, dict):
                values.extend(
                    answer.get("rdata", "")
                    for answer in host_data.get("TXT", {}).get("answers", [])
                )
        for nested_host, records in resolver_data.items():
            if nested_host == host:
                continue
            if not isinstance(records, dict):
                continue
            values.extend(
                answer.get("rdata", "")
                for answer in records.get("TXT", {}).get("answers", [])
            )
    if values:
        return values
    first_resolver = data.get("resolvers", [None])[0]
    return [answer.get("rdata", "") for answer in data.get("records", {}).get(first_resolver, {}).get(host, {}).get("TXT", {}).get("answers", [])]


def _mx_records(data):
    return data.get("mail", {}).get("mx", []) if isinstance(data.get("mail", {}).get("mx", []), list) else []


def rule_mx_001(data):
    mx = _mx_records(data)
    if not mx:
        return [_finding("MX-001", "yellow", 3, "No MX record was returned", ["No MX answers"], "The domain does not currently advertise mail exchangers in the public DNS view.", "Confirm the email hosting configuration and whether mail is intentionally absent.")]
    return []


def rule_mx_002(data):
    mx = _mx_records(data)
    for item in mx:
        if item.get("rdata") == "0 .":
            return [_finding("MX-002", "green", 3, "Null MX present", ["0 ."], "The zone advertises a null MX, which intentionally disables email delivery.", "")]
    return []


def rule_mx_003(data):
    mx = _mx_records(data)
    findings = []
    for item in mx:
        rdata = item.get("rdata", "")
        parts = rdata.split()
        if len(parts) < 2:
            continue
        host = parts[-1].rstrip(".")
        if host and not any(host == h for h, entries in ((k, v) for values in data.get("records", {}).values() for k, v in values.items()) if isinstance(entries, dict)):
            findings.append(_finding("MX-003", "red", 3, "An MX target does not resolve", [host], "A mail exchanger advertised in MX records does not resolve to a reachable address in the DNS data.", "Fix the MX target or remove the stale record."))
    return findings


def rule_mx_004(data):
    mx = _mx_records(data)
    findings = []
    for item in mx:
        rdata = item.get("rdata", "")
        parts = rdata.split()
        if len(parts) < 2:
            continue
        host = parts[-1].rstrip(".")
        for values in data.get("records", {}).values():
            for host_key, entries in values.items():
                if host_key == host and "CNAME" in entries:
                    findings.append(_finding("MX-004", "yellow", 3, "MX target is a CNAME", [host], "An MX target is also a CNAME, which violates the standard and can cause mail delivery issues.", "Replace the CNAME MX target with a direct A/AAAA record or a proper provider destination."))
    return findings


def rule_mx_005(data):
    mx = _mx_records(data)
    if mx and len(mx) == 1:
        return [_finding("MX-005", "yellow", 3, "Only one MX host is configured", ["Single MX target only"], "A single mail exchanger gives less redundancy and can increase service risk.", "Add another MX target so mail is resilient.")]
    return []


def rule_mx_006(data):
    providers = data.get("mail", {}).get("providers", [])
    if providers:
        return [_finding("MX-006", "green", 3, "Mail provider identified", providers, "The MX configuration matches a known provider, which helps confirm the mail hosting setup.", "")]
    return []


def rule_spf_001(data):
    txt_values = _text_records(data)
    if not any(value.lower().startswith("v=spf1") for value in txt_values):
        return [_finding("SPF-001", "red", 3, "No SPF record", ["No SPF TXT found"], "The domain does not publish an SPF record, so mail senders cannot validate the allowed mail servers.", "Add an SPF TXT record with the allowed mail servers and relays.")]
    return []


def rule_spf_002(data):
    txt_values = _text_records(data)
    spf = [value for value in txt_values if value.lower().startswith("v=spf1")]
    if len(spf) > 1:
        return [_finding("SPF-002", "red", 3, "More than one SPF record", spf[:3], "The zone publishes more than one SPF record, which violates the standard and creates ambiguity.", "Keep only one SPF record for the domain.")]
    return []


def rule_spf_003(data):
    txt_values = _text_records(data)
    spf = [value for value in txt_values if value.lower().startswith("v=spf1")]
    if not spf:
        return []
    text = spf[0]
    match = re.search(r"(?:^|\s)([~?+\-])?all(?:\s|$)", text, re.IGNORECASE)
    if not match:
        return [_finding("SPF-003", "yellow", 3, "SPF lacks an explicit all qualifier", [text], "The SPF rule set does not explicitly state how to handle unlisted senders.", "Add an explicit all qualifier such as -all or ~all.")]
    qualifier = (match.group(1) or "+").lower()
    if qualifier == "-":
        return [_finding("SPF-003", "green", 3, "SPF all qualifier is strict", [text], "The SPF policy explicitly rejects any sender not listed in the record.", "")]
    if qualifier == "+":
        return [_finding("SPF-003", "red", 3, "SPF all qualifier allows all senders", [text], "The SPF policy explicitly allows unknown senders, which undermines the domain's mail validation boundary.", "Change the policy to -all or ~all unless the environment is intentionally permissive.")]
    return [_finding("SPF-003", "yellow", 3, "SPF all qualifier is permissive", [text], "The SPF policy is not strict about unknown senders.", "Tighten the SPF policy if the domain should reject unauthorized mail.")]


def rule_spf_004(data):
    txt_values = _text_records(data)
    for value in txt_values:
        if value.lower().startswith("v=spf1"):
            count = len(re.findall(r"(include|redirect|a|mx|ptr|exists|ip4|ip6)", value, flags=re.IGNORECASE))
            if count > 10:
                return [_finding("SPF-004", "red", 3, "SPF lookup count exceeds the limit", [f"Detected lookups: {count}"], "The SPF record triggers more than ten DNS lookups, which creates query amplification and can fail validation.", "Reduce SPF complexity by replacing repeated includes and redirects with tighter policies.")]
    return []


def rule_spf_005(data):
    txt_values = _text_records(data)
    for value in txt_values:
        if value.lower().startswith("v=spf1") and re.search(r"(?:^|\s)ptr(?:\s|$)", value, flags=re.IGNORECASE):
            return [_finding("SPF-005", "yellow", 3, "SPF uses ptr", [value], "The SPF record includes the ptr mechanism, which is often lower quality and harder to reason about.", "Prefer explicit IP or include-based allowlists instead of ptr.")]
    return []


def rule_spf_006(data):
    txt_values = _text_records(data)
    for value in txt_values:
        if value.lower().startswith("v=spf1"):
            includes = re.findall(r"include:([^\s]+)", value, flags=re.IGNORECASE)
            if includes:
                return [_finding("SPF-006", "yellow", 3, "SPF include target is present", includes[:5], "The SPF policy depends on an include target that should be checked for resolution and ownership.", "Verify that each included host resolves correctly and is expected to send mail.")]
    return []


def rule_spf_007(data):
    txt_values = _text_records(data)
    for value in txt_values:
        if value.lower().startswith("v=spf1"):
            for cidr in re.findall(r"ip[46]:([^\s]+)", value, flags=re.IGNORECASE):
                if '/' in cidr:
                    try:
                        prefix = int(cidr.split('/')[1])
                        if 'ip4' in value.lower() and prefix < 16:
                            return [_finding("SPF-007", "yellow", 3, "SPF range is broad", [cidr], "The SPF rule allows a very wide IP block, which is broader than most organizations need.", "Reduce the range to the smallest actual mail-sending network.")]
                        if 'ip6' in value.lower() and prefix < 32:
                            return [_finding("SPF-007", "yellow", 3, "SPF range is broad", [cidr], "The SPF rule allows a very wide IPv6 block, which is broader than most organizations need.", "Reduce the range to the smallest actual mail-sending network.")]
                    except ValueError:
                        continue
    return []


def rule_dmarc_001(data):
    dmarc = data.get("mail", {}).get("dmarc", [])
    if not dmarc:
        return [_finding("DMARC-001", "red", 3, "No DMARC record", ["No _dmarc TXT found"], "The domain does not publish a DMARC policy for rejecting or quarantining spoofed mail.", "Add a DMARC policy such as p=quarantine or p=reject.")]
    return []


def rule_dmarc_002(data):
    for item in data.get("mail", {}).get("dmarc", []):
        value = item.get("rdata", "")
        if "v=dmarc1" in value.lower() and "p=none" in value.lower():
            return [_finding("DMARC-002", "yellow", 3, "DMARC policy is p=none", [value], "The DMARC policy is set to monitor only, so spoofed mail is not actively rejected or quarantined.", "Change the policy to quarantine or reject if the domain is mail-sending.")]
    return []


def rule_dmarc_003(data):
    for item in data.get("mail", {}).get("dmarc", []):
        value = item.get("rdata", "")
        if "v=dmarc1" in value.lower() and re.search(r"p=(quarantine|reject)", value, re.IGNORECASE):
            return [_finding("DMARC-003", "green", 3, "DMARC policy is strict", [value], "The DMARC policy is configured to quarantine or reject spoofed mail.", "")]
    return []


def rule_dmarc_004(data):
    for item in data.get("mail", {}).get("dmarc", []):
        value = item.get("rdata", "")
        match = re.search(r"pct=(\d+)", value, re.IGNORECASE)
        if match and int(match.group(1)) < 100:
            return [_finding("DMARC-004", "yellow", 3, "DMARC percentage is below 100", [value], "The DMARC policy does not apply to all mail, so some spoofed mail may still be accepted.", "Increase pct to 100 unless there is a staged rollout reason.")]
    return []


def rule_dmarc_005(data):
    for item in data.get("mail", {}).get("dmarc", []):
        value = item.get("rdata", "")
        if "v=dmarc1" in value.lower() and "rua=" not in value.lower():
            return [_finding("DMARC-005", "yellow", 3, "DMARC has no rua reporting target", [value], "The DMARC policy does not include a reporting address, which reduces visibility into abuse.", "Add a rua reporting target to receive aggregate reports.")]
    return []


def rule_dmarc_006(data):
    for item in data.get("mail", {}).get("dmarc", []):
        value = item.get("rdata", "")
        if "v=dmarc1" in value.lower():
            sp = re.search(r"sp=([a-z]+)", value, re.IGNORECASE)
            p = re.search(r"p=([a-z]+)", value, re.IGNORECASE)
            if sp and p:
                order = {"none": 0, "quarantine": 1, "reject": 2}
                if order.get(sp.group(1).lower(), -1) < order.get(p.group(1).lower(), -1):
                    return [_finding("DMARC-006", "yellow", 3, "Subdomain policy is weaker than base policy", [value], "The subdomain DMARC policy is weaker than the parent policy, which can leave subdomains unprotected.", "Align sp with the parent policy or set a stricter value.")]
    return []


def rule_dkim_001(data):
    selectors = data.get("mail", {}).get("dkim_selectors", [])
    if selectors:
        return [_finding("DKIM-001", "green", 3, "DKIM selector found", selectors[:5], "A DKIM selector was discovered, suggesting the domain is signing outbound mail.", "")]
    return []


def rule_dkim_002(data):
    if not data.get("mail", {}).get("dkim_selectors"):
        return [_finding("DKIM-002", "grey", 3, "No DKIM selector was found", ["Selector probes returned no hits"], "No DKIM selector was found among the common provider names, so absence is not proven but remains unconfirmed.", "")]
    return []


def rule_mtasts_001(data):
    if data.get("mail", {}).get("mta_sts"):
        return [_finding("MTASTS-001", "green", 3, "MTA-STS record present", ["_mta-sts record found"], "The domain publishes an MTA-STS policy, which helps enforce encrypted mail transport.", "")]
    return []


def rule_mtasts_002(data):
    if not data.get("mail", {}).get("mta_sts"):
        return [_finding("MTASTS-002", "yellow", 3, "MTA-STS record missing", ["No _mta-sts policy found"], "The domain does not publish MTA-STS, which means mail transport security is not explicitly enforced.", "Add an MTA-STS policy and publish the corresponding HTTPS endpoint.")]
    return []


def rule_txt_001(data):
    services = data.get("mail", {}).get("third_party_services", [])
    if services:
        return [_finding("TXT-001", "yellow", 3, "Verification records reveal third-party services", services, "TXT records reveal third-party identity verification that can expose the services tied to the domain.", "Review the disclosed services and remove unnecessary verification records.")]
    return []


def rule_txt_002(data):
    for value in _text_records(data):
        if re.search(r"(?i)(password|passwd|secret|api[_-]?key|token|private[_-]?key)\s*[=:]\s*\S+", value):
            return [_finding("TXT-002", "red", 3, "TXT record looks secret-bearing", [value], "A TXT record appears to contain credentials or API material in plaintext.", "Remove or rotate the exposed secret and move it to a protected secret store.")]
    return []
