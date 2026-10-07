import shlex
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import ALLOWED_COMMANDS, MAX_OUTPUT_BYTES


@dataclass
class CommandRecord:
    id: str
    stage: str
    label: str
    argv: list[str]
    command_line: str
    started_at: str
    duration_ms: int
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    truncated: bool = False
    cancelled: bool = False
    tool_missing: bool = False


GLOBAL_SEMAPHORE = threading.Semaphore(8)


def _truncate_output(data: str) -> tuple[str, bool]:
    if len(data.encode("utf-8")) <= MAX_OUTPUT_BYTES:
        return data, False
    return data[: MAX_OUTPUT_BYTES // 2], True


def run(argv: list[str], timeout: int, stage: str, label: str) -> CommandRecord:
    if not isinstance(argv, list) or not argv:
        raise ValueError("argv must be a non-empty list.")
    if argv[0] not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not allowed: {argv[0]}")

    command_id = uuid.uuid4().hex[:12]
    started = datetime.now(timezone.utc)
    record = CommandRecord(
        id=command_id,
        stage=stage,
        label=label,
        argv=list(argv),
        command_line=shlex.join(argv),
        started_at=started.isoformat(),
        duration_ms=0,
    )

    with GLOBAL_SEMAPHORE:
        began = datetime.now(timezone.utc)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                errors="replace",
            )
            record.exit_code = completed.returncode
            record.stdout, record.truncated = _truncate_output(completed.stdout or "")
            record.stderr, _ = _truncate_output(completed.stderr or "")
            if record.truncated:
                record.stderr = record.stderr + ("\n[truncated]" if record.stderr else "[truncated]")
        except subprocess.TimeoutExpired as exc:
            record.timed_out = True
            record.exit_code = None
            record.stdout, record.truncated = _truncate_output((exc.stdout or "") if isinstance(exc.stdout, str) else "")
            record.stderr, _ = _truncate_output((exc.stderr or "") if isinstance(exc.stderr, str) else "")
        except FileNotFoundError:
            record.tool_missing = True
            record.exit_code = 127
            record.stderr = f"{argv[0]} is not installed or not available on PATH."

        record.duration_ms = int((datetime.now(timezone.utc) - began).total_seconds() * 1000)

    return record
