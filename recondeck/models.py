from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Stage:
    id: int
    name: str
    status: str = "waiting"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    id: str
    flag: str
    stage: int
    title: str
    evidence: list[str] = field(default_factory=list)
    why: str = ""
    fix: str = ""
    refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scan:
    id: str
    target: dict[str, Any]
    options: dict[str, Any]
    status: str = "queued"
    created_at: str = ""
    finished_at: Optional[str] = None
    stages: list[Stage] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    commands: list[dict[str, Any]] = field(default_factory=list)
    coverage: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "options": self.options,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "stages": [stage.to_dict() if hasattr(stage, "to_dict") else stage for stage in self.stages],
            "findings": [finding.to_dict() if hasattr(finding, "to_dict") else finding for finding in self.findings],
            "data": self.data,
            "commands": self.commands,
            "coverage": self.coverage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scan":
        return cls(
            id=data["id"],
            target=data.get("target", {}),
            options=data.get("options", {}),
            status=data.get("status", "queued"),
            created_at=data.get("created_at", ""),
            finished_at=data.get("finished_at"),
            stages=[Stage(**stage) for stage in data.get("stages", [])],
            findings=[Finding(**finding) for finding in data.get("findings", [])],
            data=data.get("data", {}),
            commands=data.get("commands", []),
            coverage=data.get("coverage", []),
        )
