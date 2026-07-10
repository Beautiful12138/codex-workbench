from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _YamlRecord:
    kind: str
    path: Path
    relative_path: str
    data: dict[str, Any] | None
    error: str | None = None

    @property
    def id(self) -> str:
        if not self.data:
            return ""
        value = self.data.get("id", "")
        return str(value).strip() if value is not None else ""

    @property
    def title(self) -> str:
        if not self.data:
            return ""
        value = self.data.get("title", "")
        return str(value).strip() if value is not None else ""


@dataclass(frozen=True)
class _IndexSnapshot:
    requirements: list[_YamlRecord]
    tasks: list[_YamlRecord]
    evidences: list[_YamlRecord]
    archives: list[_YamlRecord]
    materials: list[dict[str, Any]]
    discoveries: list[_YamlRecord]
    services: list[dict[str, Any]]
    actions: list[_YamlRecord]
    changes: list[_YamlRecord]
    decisions: list[_YamlRecord]
    suspicions: list[_YamlRecord]
    conflicts: list[str]
