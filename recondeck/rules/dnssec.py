from __future__ import annotations

from recondeck.models import Finding


def _finding(rule_id: str, flag: str, stage: int, title: str, evidence, why: str, fix: str = "", refs=None):
    refs = refs or []
    return Finding(id=rule_id, flag=flag, stage=stage, title=title, evidence=list(evidence), why=why, fix=fix, refs=refs)


def rule_dnssec_001(data):
    dnssec = data.get("dnssec", {})
    if not dnssec.get("dnskey") and not dnssec.get("ds"):
        return [_finding("DNSSEC-001", "yellow", 4, "DNSSEC is not enabled", ["No DS or DNSKEY values found"], "The zone does not currently advertise DS or DNSKEY records, so DNSSEC validation is likely not enabled.", "Publish DS/DNSKEY data for the zone and ensure the registrar chain is correct.")]
    return []


def rule_dnssec_002(data):
    dnssec = data.get("dnssec", {})
    if dnssec.get("dnskey") or dnssec.get("ds"):
        if data.get("dnssec", {}).get("validated"):
            return [_finding("DNSSEC-002", "green", 4, "DNSSEC validation succeeded", ["ad flag set on validation query"], "A validating resolver reported the ad flag, confirming the DNSSEC chain validated successfully.", "")]
    return []


def rule_dnssec_003(data):
    dnssec = data.get("dnssec", {})
    if dnssec.get("ds") and dnssec.get("broken"):
        return [_finding("DNSSEC-003", "red", 4, "DNSSEC chain validation breaks", ["DS exists but validation failed"], "A DS record exists but validation breaks, which suggests the parent-child chain is incomplete or inconsistent.", "Fix the DS publication and secure the chain between parent and child zone.")]
    return []


def rule_dnssec_004(data):
    dnssec = data.get("dnssec", {})
    weak = []
    for key_name in ("dnskey", "ds"):
        for answer in dnssec.get(key_name, []):
            rdata = answer.get("rdata", "")
            parts = rdata.split()
            if len(parts) >= 2:
                try:
                    algorithm = int(parts[1])
                    if algorithm in {1, 3, 5, 6, 7}:
                        weak.append(f"{key_name}:{algorithm}")
                except ValueError:
                    pass
    if weak:
        return [_finding("DNSSEC-004", "yellow", 4, "Weak DNSSEC algorithm present", weak, "The zone uses a legacy or weak DNSSEC algorithm that should be upgraded for stronger validation.", "Replace weak DS/DNSKEY algorithms with stronger modern choices.")]
    return []


def rule_caa_001(data):
    if data.get("records", {}).get(data.get("resolvers", [None])[0], {}).get(data.get("target", {}).get("hostname"), {}).get("CAA"):
        return [_finding("CAA-001", "green", 4, "CAA record present", ["CAA record in apex data"], "The domain publishes a CAA record, which constrains which certificate authorities can issue certificates.", "")]
    return []


def rule_caa_002(data):
    if not data.get("records", {}).get(data.get("resolvers", [None])[0], {}).get(data.get("target", {}).get("hostname"), {}).get("CAA"):
        return [_finding("CAA-002", "yellow", 4, "CAA record missing", ["No CAA answer"], "The zone does not advertise a CAA restriction, so any CA may issue a certificate unless another control exists.", "Add a CAA policy to restrict certificate issuance.")]
    return []
