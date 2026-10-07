from __future__ import annotations

import secrets

from recondeck.config import RESOLVERS
from recondeck.digparse import dig_query
from recondeck.runner import run
from recondeck.stages import log_command
from recondeck.validators import parse_target


def run_stage(scan):
    if "target" not in scan.target:
        parsed = parse_target(scan.target.get("input") or scan.target.get("hostname"))
        scan.target.update(parsed)
    scan.coverage.append({"check": "prepare_target", "status": "ran", "detail": f"Target normalized to {scan.target['hostname']}"})

    dig_check = run(["dig", "-v"], timeout=5, stage="prepare", label="dig_version")
    if dig_check.exit_code not in (0, 1):
        raise ValueError("dig is not installed. Run: sudo apt install dnsutils")
    log_command(scan, dig_check)

    whois_check = run(["whois", "--version"], timeout=5, stage="prepare", label="whois_version")
    log_command(scan, whois_check)
    if whois_check.exit_code not in (0, 1):
        scan.data.setdefault("whois", {}).setdefault("status", "unavailable")

    resolvers = []
    for resolver in RESOLVERS:
        probe = run(["dig", "@" + resolver, ".", "NS", "+short", "+time=3", "+tries=1"], timeout=8, stage="prepare", label=f"resolver_probe_{resolver}")
        log_command(scan, probe)
        if probe.stdout.strip() or probe.exit_code == 0:
            resolvers.append(resolver)
    if not resolvers:
        raise ValueError("no network or DNS access")

    scan.data["resolvers"] = resolvers
    scan.coverage.append({"check": "resolver_probe", "status": "ran", "detail": f"{len(resolvers)} resolvers responded"})

    label = "r" + secrets.token_hex(3)
    domain = scan.target["hostname"]
    wildcard = {"a": [], "aaaa": [], "cname": []}
    for qtype in ("A", "AAAA"):
        result = dig_query(f"{label}.{domain}", qtype, server=resolvers[0])
        for answer in result.answers:
            wildcard[qtype.lower()].append(answer["rdata"])
    scan.data["wildcard"] = wildcard if wildcard["a"] or wildcard["aaaa"] else None

    scan.findings.append({
        "id": "PREP-001",
        "flag": "green",
        "stage": 0,
        "title": "Resolver and tool checks passed",
        "evidence": [f"dig available; {len(resolvers)} working resolver(s)"],
        "why": "The required DNS tooling is available and at least one public resolver is answering.",
        "fix": "",
        "refs": [],
    })
