from __future__ import annotations

from recondeck.digparse import dig_query
from recondeck.stages import log_command


def run_stage(scan):
    domain = scan.target["hostname"]
    resolver = scan.data["resolvers"][0]
    dnskey_result = dig_query(domain, "DNSKEY", server=resolver, dnssec=True)
    ds_result = dig_query(domain, "DS", server=resolver, dnssec=True)
    nsec3param_result = dig_query(domain, "NSEC3PARAM", server=resolver, dnssec=True)
    log_command(scan, dnskey_result.command)
    log_command(scan, ds_result.command)
    log_command(scan, nsec3param_result.command)
    dnssec = {
        "dnskey": dnskey_result.answers,
        "ds": ds_result.answers,
        "nsec3param": nsec3param_result.answers,
    }
    scan.data["dnssec"] = dnssec
    scan.coverage.append({"check": "dnssec_records", "status": "ran", "detail": "DNSSEC material collected"})

    scan.findings.append({
        "id": "DNSSEC-001",
        "flag": "green" if dnssec["dnskey"] or dnssec["ds"] else "yellow",
        "stage": 4,
        "title": "DNSSEC material checked",
        "evidence": [f"DNSKEY {len(dnssec['dnskey'])}", f"DS {len(dnssec['ds'])}"],
        "why": "DNSSEC records were queried to confirm whether the zone is signed or not.",
        "fix": "If DNSSEC is absent, enable signed zones and DS publication." if not (dnssec["dnskey"] or dnssec["ds"]) else "",
        "refs": [],
    })
