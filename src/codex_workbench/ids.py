from __future__ import annotations

import re
from pathlib import Path

from .workspace import resolve_workspace_path


def allocate_requirement_id(workspace_root: str | Path, timestamp: str) -> str:
    date_part = _compact_date(timestamp)
    sequence = _next_sequence(_iter_package_ids(workspace_root), f"REQ-{date_part}-")
    return f"REQ-{date_part}-{sequence:03d}"


def allocate_task_id(workspace_root: str | Path, requirement_id: str, timestamp: str) -> str:
    date_part = _compact_date(timestamp)
    prefix = f"{requirement_id}-TASK-{date_part}-"
    sequence = _next_sequence(_iter_package_ids(workspace_root), prefix)
    return f"{prefix}{sequence:03d}"


def _compact_date(timestamp: str) -> str:
    date_part = timestamp.strip()[:10].replace("-", "")
    if not re.fullmatch(r"\d{8}", date_part):
        raise ValueError(f"invalid_timestamp_for_id: {timestamp}")
    return date_part


def _next_sequence(ids: set[str], prefix: str) -> int:
    max_seen = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{3,}})$")
    for item in ids:
        match = pattern.fullmatch(item)
        if match:
            max_seen = max(max_seen, int(match.group(1)))
    return max_seen + 1


def _iter_package_ids(workspace_root: str | Path) -> set[str]:
    root = Path(workspace_root)
    package_ids: set[str] = set()
    for directory in _iter_direct_package_dirs(resolve_workspace_path(root, "docs/active")):
        package_ids.add(directory.name)
    archive_root = resolve_workspace_path(root, "docs/archive")
    if archive_root.exists():
        for version_dir in archive_root.iterdir():
            if version_dir.is_dir():
                for directory in _iter_direct_package_dirs(version_dir):
                    package_ids.add(directory.name)
    return package_ids


def _iter_direct_package_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.iterdir() if path.is_dir()]
