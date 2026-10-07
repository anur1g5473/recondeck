from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .models import Scan


def scan_root() -> Path:
    root = PROJECT_ROOT / "scans"
    root.mkdir(parents=True, exist_ok=True)
    return root


def new_scan_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]


def ensure_scan_dir(scan_id: str) -> Path:
    scan_dir = scan_root() / scan_id
    (scan_dir / "raw").mkdir(parents=True, exist_ok=True)
    return scan_dir


def save_scan(scan: Scan) -> Path:
    scan_dir = ensure_scan_dir(scan.id)
    temp_path = scan_dir / ".scan.json.tmp"
    temp_path.write_text(json.dumps(scan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    final_path = scan_dir / "scan.json"
    os.replace(temp_path, final_path)
    return final_path


def load_scan(scan_id: str) -> Scan:
    data = json.loads((scan_root() / scan_id / "scan.json").read_text(encoding="utf-8"))
    return Scan.from_dict(data)


def write_raw_output(scan_id: str, command_id: str, text: str) -> Path:
    target = ensure_scan_dir(scan_id) / "raw" / f"{command_id}.txt"
    target.write_text(text, encoding="utf-8")
    return target


def list_recent_scans() -> list[str]:
    base = scan_root()
    if not base.exists():
        return []
    return sorted([item.name for item in base.iterdir() if (item / "scan.json").exists()], reverse=True)
