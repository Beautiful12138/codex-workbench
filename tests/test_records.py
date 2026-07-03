from __future__ import annotations

from pathlib import Path

import pytest

import codex_workbench.records as records_module
from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.records import create_action_note


def test_record_create_rejects_concurrent_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write = records_module.write_text_utf8_atomic
    injected = False

    def racing_write(path: Path, content: str, **kwargs: object) -> None:
        nonlocal injected
        if not injected and path.name == "ACT-001.yaml":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "schema_version: '0.1'\nid: ACT-OTHER\ntitle: 其他动作\nupdated_at: 2026-07-01\n"
                "summary: 其他窗口写入。\naction_type: maintenance_action\nstatus: executed\n",
                encoding="utf-8",
            )
            injected = True
        original_write(path, content, **kwargs)

    monkeypatch.setattr(records_module, "write_text_utf8_atomic", racing_write)

    with pytest.raises(WorkbenchError) as exc_info:
        create_action_note(
            tmp_path,
            action_id="ACT-001",
            title="记录动作",
            summary="记录一次辅助动作。",
            action_type="maintenance_action",
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.ALREADY_EXISTS


def test_record_create_rolls_back_yaml_when_markdown_conflicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write = records_module.write_text_utf8_atomic
    action_yaml = tmp_path / "docs" / "actions" / "ACT-001.yaml"
    action_md = tmp_path / "docs" / "actions" / "ACT-001.md"

    def fail_on_markdown(path: Path, content: str, **kwargs: object) -> None:
        if path == action_md:
            action_md.write_text("其他窗口创建了 action.md。\n", encoding="utf-8")
            raise WorkbenchError(ErrorCode.ALREADY_EXISTS, "already_exists", exit_code=2)
        original_write(path, content, **kwargs)

    monkeypatch.setattr(records_module, "write_text_utf8_atomic", fail_on_markdown)

    with pytest.raises(WorkbenchError) as exc_info:
        create_action_note(
            tmp_path,
            action_id="ACT-001",
            title="记录动作",
            summary="记录一次辅助动作。",
            action_type="maintenance_action",
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.ALREADY_EXISTS
    assert not action_yaml.exists()
    assert action_md.read_text(encoding="utf-8") == "其他窗口创建了 action.md。\n"
