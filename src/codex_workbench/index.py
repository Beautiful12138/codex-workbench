from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._index_records import collect_snapshot as _collect_snapshot
from ._index_views import (
    render_current as _render_current,
    render_index as _render_index,
    render_recovery as _render_recovery,
)
from .io import read_text_utf8, write_text_utf8_atomic
from .workspace import resolve_workspace_path


INDEX_PATH = "docs/generated/index.md"
RECOVERY_PATH = "docs/generated/recovery.md"
CURRENT_PATH = "CURRENT.md"

__all__ = [
    "IndexCheckResult",
    "IndexWriteResult",
    "check_generated_views",
    "generate_index_views",
]


@dataclass(frozen=True)
class IndexWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool
    current_text: str
    index_text: str
    recovery_text: str
    conflicts: list[str]


@dataclass(frozen=True)
class IndexCheckResult:
    clean: bool
    status: str
    messages: list[str]
    conflicts: list[str]


def generate_index_views(
    workspace_root: str | Path,
    *,
    dry_run: bool = False,
) -> IndexWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    snapshot = _collect_snapshot(root)
    current_text = _render_current(snapshot)
    index_text = _render_index(snapshot)
    recovery_text = _render_recovery(snapshot)
    current_path = resolve_workspace_path(root, CURRENT_PATH)
    index_path = resolve_workspace_path(root, INDEX_PATH)
    recovery_path = resolve_workspace_path(root, RECOVERY_PATH)

    if not dry_run:
        write_text_utf8_atomic(current_path, current_text)
        write_text_utf8_atomic(index_path, index_text)
        write_text_utf8_atomic(recovery_path, recovery_text)

    return IndexWriteResult(
        paths=(current_path, index_path, recovery_path),
        dry_run=dry_run,
        current_text=current_text,
        index_text=index_text,
        recovery_text=recovery_text,
        conflicts=snapshot.conflicts,
    )


def check_generated_views(workspace_root: str | Path) -> IndexCheckResult:
    root = Path(workspace_root).expanduser().resolve()
    expected = generate_index_views(root, dry_run=True)
    messages: list[str] = []
    for relative_path, expected_text in (
        (CURRENT_PATH, expected.current_text),
        (INDEX_PATH, expected.index_text),
        (RECOVERY_PATH, expected.recovery_text),
    ):
        path = resolve_workspace_path(root, relative_path)
        if not path.exists():
            messages.append(f"missing: {relative_path}")
            continue
        if read_text_utf8(path) != expected_text:
            messages.append(f"stale: {relative_path}")

    messages.extend(f"conflict: {item}" for item in expected.conflicts)
    if expected.conflicts:
        status = "conflict"
    elif messages:
        status = "stale"
    else:
        status = "clean"
    return IndexCheckResult(
        clean=not messages,
        status=status,
        messages=messages,
        conflicts=expected.conflicts,
    )
