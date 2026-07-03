from __future__ import annotations

from pathlib import Path

import pytest

from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.io import (
    read_text_utf8,
    read_text_with_version,
    read_yaml,
    read_yaml_with_version,
    write_text_utf8_atomic,
    write_yaml_atomic,
)


def test_atomic_text_write_round_trips_utf8(tmp_path: Path) -> None:
    target = tmp_path / "CURRENT.md"

    result = write_text_utf8_atomic(target, "role: 最近工作面板\n")

    assert result.path == target
    assert result.changed is True
    assert result.dry_run is False
    assert read_text_utf8(target) == "role: 最近工作面板\n"


def test_dry_run_text_write_does_not_create_file(tmp_path: Path) -> None:
    target = tmp_path / "missing.md"

    result = write_text_utf8_atomic(target, "content\n", dry_run=True)

    assert result.path == target
    assert result.changed is False
    assert result.dry_run is True
    assert not target.exists()


def test_dry_run_text_write_does_not_replace_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "CURRENT.md"
    target.write_text("old\n", encoding="utf-8")

    write_text_utf8_atomic(target, "new\n", dry_run=True)

    assert target.read_text(encoding="utf-8") == "old\n"


def test_dry_run_yaml_write_does_not_create_file(tmp_path: Path) -> None:
    target = tmp_path / "services" / "registry.yaml"

    result = write_yaml_atomic(target, {"services": []}, dry_run=True)

    assert result.path == target
    assert result.changed is False
    assert result.dry_run is True
    assert not target.exists()


def test_yaml_round_trip_preserves_unicode(tmp_path: Path) -> None:
    target = tmp_path / "services" / "registry.yaml"
    data = {"services": [{"name": "codex-workbench", "purpose": "最近工作面板"}]}

    write_yaml_atomic(target, data)

    assert read_yaml(target) == data


def test_text_write_rejects_stale_expected_version(tmp_path: Path) -> None:
    target = tmp_path / "task.yaml"
    target.write_text("stage: draft\n", encoding="utf-8")
    snapshot = read_text_with_version(target)
    target.write_text("stage: ready\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        write_text_utf8_atomic(target, "stage: in_progress\n", expected_version=snapshot.version)

    assert exc_info.value.code.value == "concurrent_update"
    assert target.read_text(encoding="utf-8") == "stage: ready\n"


def test_yaml_write_rejects_stale_expected_version(tmp_path: Path) -> None:
    target = tmp_path / "task.yaml"
    write_yaml_atomic(target, {"stage": "draft"})
    snapshot = read_yaml_with_version(target)
    write_yaml_atomic(target, {"stage": "ready"})

    with pytest.raises(WorkbenchError) as exc_info:
        write_yaml_atomic(target, {"stage": "in_progress"}, expected_version=snapshot.version)

    assert exc_info.value.code.value == "concurrent_update"
    assert read_yaml(target) == {"stage": "ready"}


def test_create_only_text_write_rejects_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "task.md"
    target.write_text("existing\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        write_text_utf8_atomic(target, "replacement\n", create_only=True)

    assert exc_info.value.code.value == "already_exists"
    assert target.read_text(encoding="utf-8") == "existing\n"


def test_read_text_utf8_reports_structured_io_error(tmp_path: Path) -> None:
    with pytest.raises(WorkbenchError) as exc_info:
        read_text_utf8(tmp_path / "missing.md")

    assert exc_info.value.code is ErrorCode.IO_ERROR
    assert exc_info.value.exit_code == 1


def test_read_yaml_reports_structured_parse_error(tmp_path: Path) -> None:
    target = tmp_path / "broken.yaml"
    target.write_text("services: [\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        read_yaml(target)

    assert exc_info.value.code is ErrorCode.PARSE_ERROR
    assert exc_info.value.exit_code == 2


def test_text_write_reports_structured_io_error_when_parent_is_file(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        write_text_utf8_atomic(blocked_parent / "CURRENT.md", "content\n")

    assert exc_info.value.code is ErrorCode.IO_ERROR
    assert exc_info.value.exit_code == 1


def test_yaml_write_reports_structured_io_error_when_parent_is_file(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        write_yaml_atomic(blocked_parent / "registry.yaml", {"services": []})

    assert exc_info.value.code is ErrorCode.IO_ERROR
    assert exc_info.value.exit_code == 1
