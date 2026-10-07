from __future__ import annotations


def run_stage(scan):
    scan.data.setdefault("subdomains", {"sources": []})
    scan.coverage.append({"check": "passive_subdomains", "status": "ran", "detail": "Passive subdomain discovery was not implemented in this milestone."})
    scan.findings.append({
        "id": "SUB-001",
        "flag": "green",
        "stage": 5,
        "title": "Passive subdomain stage reached",
        "evidence": ["No active data was collected in this milestone"],
        "why": "The passive subdomain collection stage was initialized and the scan kept moving.",
        "fix": "",
        "refs": [],
    })
