from __future__ import annotations

from recondeck.store import write_raw_output


def log_command(scan, record):
    payload = {
        "id": record.id,
        "stage": getattr(record, "stage", "unknown"),
        "label": getattr(record, "label", ""),
        "command_line": getattr(record, "command_line", ""),
        "duration_ms": getattr(record, "duration_ms", 0),
        "exit_code": getattr(record, "exit_code", None),
        "timed_out": getattr(record, "timed_out", False),
        "truncated": getattr(record, "truncated", False),
    }
    scan.commands.append(payload)
    if hasattr(record, "stdout") or hasattr(record, "stderr"):
        write_raw_output(scan.id, record.id, (getattr(record, "stdout", "") or "") + (getattr(record, "stderr", "") or ""))
