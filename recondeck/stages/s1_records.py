from __future__ import annotations

from recondeck.digparse import dig_query
from recondeck.stages import log_command

RECORD_TYPES = ["A", "AAAA", "NS", "MX", "TXT", "SOA", "CNAME", "CAA", "HTTPS", "SVCB", "SRV"]
SPECIAL_SRV = [
    "_sip._tcp", "_sip._udp", "_sips._tcp", "_ldap._tcp", "_kerberos._tcp", "_kerberos._udp",
    "_xmpp-client._tcp", "_xmpp-server._tcp", "_autodiscover._tcp", "_imap._tcp", "_imaps._tcp",
    "_submission._tcp", "_pop3s._tcp", "_caldavs._tcp", "_carddavs._tcp", "_matrix._tcp",
]


def _record_entry(scan, result, host, qtype):
    log_command(scan, result.command)
    return {"status": result.status, "answers": result.answers, "flags": result.flags, "error": result.error}


def run_stage(scan):
    domain = scan.target["hostname"]
    resolvers = scan.data.get("resolvers", [])
    records = {}

    for resolver in resolvers:
        records.setdefault(resolver, {})
        for qtype in RECORD_TYPES:
            for host in [domain, "www." + domain]:
                result = dig_query(host, qtype, server=resolver)
                records[resolver].setdefault(host, {})[qtype] = _record_entry(scan, result, host, qtype)
        for service in SPECIAL_SRV:
            fqdn = f"{service}.{domain}"
            result = dig_query(fqdn, "SRV", server=resolver)
            records[resolver].setdefault(fqdn, {})["SRV"] = _record_entry(scan, result, fqdn, "SRV")

    scan.data["records"] = records
    scan.coverage.append({"check": "core_records", "status": "ran", "detail": f"Queried {len(RECORD_TYPES) + len(SPECIAL_SRV)} record classes"})

    evidence = []
    for resolver, per_host in records.items():
        for host, qmap in per_host.items():
            for qtype, payload in qmap.items():
                if payload.get("answers"):
                    evidence.append(f"{resolver} {host} {qtype}: {len(payload['answers'])} answers")
    scan.findings.append({
        "id": "RCD-001",
        "flag": "green",
        "stage": 1,
        "title": "Core DNS records queried",
        "evidence": evidence[:8] or ["No record data returned"],
        "why": "The public resolvers answered core DNS questions for the target and www host.",
        "fix": "",
        "refs": [],
    })
