from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import ErrorCode, WorkbenchError


WORKSPACE_MARKERS = ("AGENTS.md", "CURRENT.md", "services/registry.yaml")


def is_workspace_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in WORKSPACE_MARKERS)


def _candidate_roots(start: Path) -> Iterable[Path]:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    yield current
    yield from current.parents


def find_workspace_root(start: str | Path | None = None) -> Path:
    initial = Path.cwd() if start is None else Path(start)

    for candidate in _candidate_roots(initial):
        if is_workspace_root(candidate):
            return candidate

    raise WorkbenchError(
        ErrorCode.WORKSPACE_NOT_FOUND,
        f"未找到 codex-workbench 工作区：{initial}",
        exit_code=2,
    )


def resolve_workspace_path(workspace_root: str | Path, candidate: str | Path) -> Path:
    root = Path(workspace_root).expanduser().resolve()
    raw_path = Path(candidate).expanduser()
    path = raw_path if raw_path.is_absolute() else root / raw_path
    resolved = path.resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.PATH_OUTSIDE_WORKSPACE,
            f"路径不在工作区内：{candidate}",
            exit_code=2,
        ) from exc

    return resolved
