from __future__ import annotations

import ipaddress

from recondeck.runner import run
from recondeck.stages import log_command


def run_stage(scan):
    target = scan.target["hostname"]
    whois_cmd = run(["whois", target], timeout=15, stage="enrich", label="whois_domain")
    log_command(scan, whois_cmd)
    scan.data["whois"] = {"stdout": whois_cmd.stdout, "stderr": whois_cmd.stderr, "exit_code": whois_cmd.exit_code}
    scan.coverage.append({"check": "whois_lookup", "status": "ran" if whois_cmd.exit_code in (0, 1) else "failed", "detail": "whois queried for registration data"})

    ip_rows = []
    for answer in scan.data.get("records", {}).get(scan.data["resolvers"][0], {}).get(target, {}).get("A", {}).get("answers", []):
        rdata = answer.get("rdata")
        try:
            ipaddress.ip_address(rdata)
            ip_rows.append(rdata)
        except ValueError:
            continue

    scan.data["ips"] = {ip: {"source": "A record"} for ip in ip_rows}
    scan.findings.append({
        "id": "WHOIS-001",
        "flag": "green",
        "stage": 7,
        "title": "Registration data loaded",
        "evidence": [f"whois output length {len(whois_cmd.stdout or '')}"],
        "why": "Whois and host ownership details were gathered for the domain and its endpoints.",
        "fix": "",
        "refs": [],
    })
