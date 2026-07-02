from __future__ import annotations

from pathlib import Path

import pytest

from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.workspace import find_workspace_root, resolve_workspace_path


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text("services: []\n", encoding="utf-8")


def test_find_workspace_root_from_nested_directory(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    nested = tmp_path / "docs" / "tasks"
    nested.mkdir(parents=True)

    assert find_workspace_root(nested) == tmp_path


def test_find_workspace_root_from_file_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    task_file = tmp_path / "docs" / "tasks" / "TASK-1.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("# task\n", encoding="utf-8")

    assert find_workspace_root(task_file) == tmp_path


def test_find_workspace_root_reports_structured_error(tmp_path: Path) -> None:
    with pytest.raises(WorkbenchError) as exc_info:
        find_workspace_root(tmp_path)

    assert exc_info.value.code is ErrorCode.WORKSPACE_NOT_FOUND
    assert exc_info.value.exit_code == 2


def test_resolve_workspace_path_accepts_relative_inside_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    resolved = resolve_workspace_path(tmp_path, "docs/tasks/TASK-1.md")

    assert resolved == tmp_path / "docs" / "tasks" / "TASK-1.md"


def test_resolve_workspace_path_accepts_absolute_inside_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    inside = tmp_path / "CURRENT.md"

    assert resolve_workspace_path(tmp_path, inside) == inside


def test_resolve_workspace_path_rejects_parent_escape(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        resolve_workspace_path(tmp_path, "../outside.md")

    assert exc_info.value.code is ErrorCode.PATH_OUTSIDE_WORKSPACE


def test_resolve_workspace_path_rejects_absolute_outside_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    outside = tmp_path.parent / "outside.md"

    with pytest.raises(WorkbenchError) as exc_info:
        resolve_workspace_path(tmp_path, outside)

    assert exc_info.value.code is ErrorCode.PATH_OUTSIDE_WORKSPACE
