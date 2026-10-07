from __future__ import annotations

from recondeck.digparse import dig_query
from recondeck.runner import run
from recondeck.stages import log_command


def run_stage(scan):
    domain = scan.target["hostname"]
    resolver = scan.data["resolvers"][0]
    trace = run(["dig", "+trace", "+nodnssec", domain, "NS"], timeout=15, stage="nameservers", label="dig_trace_ns")
    log_command(scan, trace)
    scan.data.setdefault("nameservers", {})["trace"] = {"status": trace.exit_code, "stdout": trace.stdout, "stderr": trace.stderr}

    ns_result = dig_query(domain, "NS", server=resolver)
    log_command(scan, ns_result.command)

    ns_names = []
    for answer in ns_result.answers:
        if answer["type"] == "NS":
            ns_names.append(answer["rdata"].rstrip("."))
    scan.data["nameservers"]["names"] = ns_names
    scan.coverage.append({"check": "name_server_list", "status": "ran", "detail": f"{len(ns_names)} nameserver(s) returned"})

    for ns_name in ns_names:
        for qtype in ("A", "AAAA"):
            result = dig_query(ns_name, qtype, server=resolver)
            scan.data["nameservers"].setdefault(ns_name, {})[qtype] = result.answers
            log_command(scan, result.command)

    scan.findings.append({
        "id": "NS-002",
        "flag": "green" if len(ns_names) >= 2 else "red",
        "stage": 2,
        "title": "Nameserver data collected",
        "evidence": ns_names or ["No nameservers returned"],
        "why": "The delegation data identifies the nameservers that serve the domain.",
        "fix": "Ensure at least two responsive nameservers are present and delegated." if len(ns_names) < 2 else "",
        "refs": [],
    })
