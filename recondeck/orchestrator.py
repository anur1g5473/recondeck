from __future__ import annotations

import importlib
import json
import sys
import uuid
from datetime import datetime, timezone

from .models import Scan, Stage
from .store import ensure_scan_dir, save_scan, write_raw_output
from .validators import parse_target

STAGE_NAMES = [
    "Prepare",
    "Core records",
    "Nameservers",
    "Email",
    "DNSSEC",
    "Passive subdomains",
    "Active probing",
    "Enrichment",
    "Analysis",
    "Report",
]


def new_scan_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _log_command(scan: Scan, record):
    scan.commands.append(
        {
            "id": record.id,
            "stage": record.stage,
            "label": record.label,
            "command_line": record.command_line,
            "duration_ms": record.duration_ms,
            "exit_code": record.exit_code,
            "timed_out": record.timed_out,
            "truncated": record.truncated,
        }
    )
    write_raw_output(scan.id, record.id, (record.stdout or "") + (record.stderr or ""))
    save_scan(scan)


def run_scan(target: str, options: dict | None = None, scan_id: str | None = None):
    options = options or {}
    target_info = parse_target(target)
    if scan_id is None:
        scan_id = f"scan-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{abs(hash(target_info['hostname'])) % 1000000}"
    scan = Scan(
        id=scan_id,
        target={"input": target, "hostname": target_info["hostname"], "registered_domain": target_info["registered_domain"], "suffix": target_info["suffix"]},
        options={"wordlist": options.get("wordlist", "small"), "active": bool(options.get("active", False)), "authorized": bool(options.get("authorized", False))},
        status="running",
        created_at=datetime.now(timezone.utc).isoformat(),
        stages=[Stage(id=i, name=name) for i, name in enumerate(STAGE_NAMES)],
        findings=[],
    )
    ensure_scan_dir(scan.id)
    save_scan(scan)

    stage_mods = [
        "recondeck.stages.s0_prepare",
        "recondeck.stages.s1_records",
        "recondeck.stages.s2_nameservers",
        "recondeck.stages.s3_email",
        "recondeck.stages.s4_dnssec",
        "recondeck.stages.s5_passive_subs",
        "recondeck.stages.s6_active",
        "recondeck.stages.s7_enrich",
    ]

    for idx, module_name in enumerate(stage_mods):
        stage = scan.stages[idx]
        stage.status = "running"
        stage.started_at = datetime.now(timezone.utc).isoformat()
        save_scan(scan)
        try:
            module = importlib.import_module(module_name)
            module.run_stage(scan)
            stage.status = "done"
            stage.note = "completed"
        except Exception as exc:
            stage.status = "failed"
            stage.note = str(exc)
            scan.coverage.append({"check": f"stage_{idx}", "status": "failed", "detail": str(exc)})
            scan.status = "failed"
        finally:
            stage.finished_at = datetime.now(timezone.utc).isoformat()
            save_scan(scan)

    # Stage 7 enrichment is not always registered; s5/s6 are simple stubs
    if not scan.status == "failed":
        scan.status = "done"
        scan.finished_at = datetime.now(timezone.utc).isoformat()
        save_scan(scan)

    return scan


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    scan = run_scan(target)
    print(json.dumps({"scan_id": scan.id, "status": scan.status, "findings": list(scan.findings)}, indent=2))
