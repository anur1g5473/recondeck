from __future__ import annotations


def run_stage(scan):
    scan.data.setdefault("active", {"enabled": bool(scan.options.get("active", False)), "status": "skipped"})
    scan.coverage.append({"check": "active_checks", "status": "skipped", "detail": "Active checks are deferred to later milestones."})
    scan.findings.append({
        "id": "AXFR-003",
        "flag": "grey",
        "stage": 6,
        "title": "Active probing not run in this milestone",
        "evidence": ["active=False or not yet implemented"],
        "why": "Active probing is deferred until the later milestone, so coverage remains grey rather than green.",
        "fix": "Enable active-probing with authorization at the later milestone.",
        "refs": [],
    })
