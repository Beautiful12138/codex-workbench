from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import codex_workbench.validation as validation_module
from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.io import read_yaml_with_version, write_yaml_atomic
from codex_workbench.models import EvidenceState
from codex_workbench.packages import set_task_stage
from codex_workbench.schema import CURRENT_SCHEMA_VERSION
from codex_workbench.validation import (
    apply_validation,
    create_evidence_record,
    set_handoff_status,
)


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )


def write_task(root: Path, **overrides: object) -> Path:
    task_dir = root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001"
    task_dir.mkdir(parents=True)
    payload: dict[str, object] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "id": "REQ-20260702-001-TASK-20260702-001",
        "requirement_id": "REQ-20260702-001",
        "title": "验证闭环",
        "created_at": "2026-07-01T09:00:00+08:00",
        "updated_at": "2026-07-01T09:00:00+08:00",
        "stage": "in_progress",
        "process_level": "standard",
        "risk_level": "standard",
        "service_refs": ["codex-workbench"],
        "validation": {"status": "not_started"},
        "handoff": {"status": "not_required"},
    }
    payload.update(overrides)
    task_yaml = task_dir / "task.yaml"
    task_yaml.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (task_dir / "task.md").write_text("# REQ-20260702-001-TASK-20260702-001 验证闭环\n", encoding="utf-8")
    return task_yaml


def read_task(root: Path) -> dict[str, object]:
    return yaml.safe_load(
        (root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )


def test_create_evidence_record_writes_schema_valid_yaml_and_markdown(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    result = create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["python -m pytest passed"],
        updated_at="2026-07-01",
    )

    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_md = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.md"
    evidence = yaml.safe_load(evidence_yaml.read_text(encoding="utf-8"))

    assert evidence_yaml in result.paths
    assert evidence_md in result.paths
    EvidenceState.model_validate(evidence)
    assert evidence["id"] == "EV-REQ-20260702-001-TASK-20260702-001"
    assert evidence["task_id"] == "REQ-20260702-001-TASK-20260702-001"
    assert evidence["key_outputs"] == ["python -m pytest passed"]
    evidence_text = evidence_md.read_text(encoding="utf-8")
    assert "## 关键输出" in evidence_text
    assert "python -m pytest passed" not in evidence_text


def test_create_evidence_record_rejects_empty_key_outputs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_evidence_record(
            tmp_path,
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            task_id="REQ-20260702-001-TASK-20260702-001",
            conclusion="passed",
            key_outputs=[],
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_key_outputs" in exc_info.value.message


@pytest.mark.parametrize("conclusion", ["not_started", "pending"])
def test_create_evidence_record_rejects_process_status_as_conclusion(
    tmp_path: Path,
    conclusion: str,
) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_evidence_record(
            tmp_path,
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            task_id="REQ-20260702-001-TASK-20260702-001",
            conclusion=conclusion,
            key_outputs=["pytest passed"],
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert f"invalid_evidence_conclusion: {conclusion}" in exc_info.value.message


def test_create_evidence_record_rejects_concurrent_existing_evidence_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    original_write = validation_module.write_text_utf8_atomic
    injected = False

    def racing_write(path: Path, content: str, **kwargs: object) -> None:
        nonlocal injected
        if not injected and path.name == "evidence.yaml":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "schema_version: '0.1'\nid: EV-OTHER\ntask_id: REQ-20260702-001-TASK-20260702-001\n"
                "conclusion: passed\nkey_outputs:\n- other\n",
                encoding="utf-8",
            )
            injected = True
        original_write(path, content, **kwargs)

    monkeypatch.setattr(validation_module, "write_text_utf8_atomic", racing_write)

    with pytest.raises(WorkbenchError) as exc_info:
        create_evidence_record(
            tmp_path,
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            task_id="REQ-20260702-001-TASK-20260702-001",
            conclusion="passed",
            key_outputs=["python -m pytest passed"],
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.ALREADY_EXISTS


def test_create_evidence_record_rolls_back_yaml_when_markdown_conflicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    original_write = validation_module.write_text_utf8_atomic
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_md = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.md"

    def fail_on_markdown(path: Path, content: str, **kwargs: object) -> None:
        if path == evidence_md:
            evidence_md.write_text("其他窗口创建了 evidence.md。\n", encoding="utf-8")
            raise WorkbenchError(ErrorCode.ALREADY_EXISTS, "already_exists", exit_code=2)
        original_write(path, content, **kwargs)

    monkeypatch.setattr(validation_module, "write_text_utf8_atomic", fail_on_markdown)

    with pytest.raises(WorkbenchError) as exc_info:
        create_evidence_record(
            tmp_path,
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            task_id="REQ-20260702-001-TASK-20260702-001",
            conclusion="passed",
            key_outputs=["python -m pytest passed"],
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.ALREADY_EXISTS
    assert not evidence_yaml.exists()
    assert evidence_md.read_text(encoding="utf-8") == "其他窗口创建了 evidence.md。\n"


@pytest.mark.parametrize("bad_ref", [".", "../archive/REQ-20260702-001-TASK-20260702-001", "TASK/001", " REQ-20260702-001-TASK-20260702-001"])
def test_evidence_refs_cannot_escape_active_package(tmp_path: Path, bad_ref: str) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_evidence_record(
            tmp_path,
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            task_id=bad_ref,
            conclusion="passed",
            key_outputs=["pytest passed"],
            updated_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert f"invalid_package_ref: {bad_ref}" in exc_info.value.message


def test_apply_validation_writes_task_validation_from_real_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["python -m pytest passed"],
        updated_at="2026-07-01",
    )

    result = apply_validation(
        tmp_path,
        task_id="REQ-20260702-001-TASK-20260702-001",
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        status="passed",
    )

    task = read_task(tmp_path)
    assert tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml" in result.paths
    assert task["validation"] == {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
        "unverified_items": [],
    }


def test_apply_validation_rejects_stale_task_yaml_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    task_yaml = write_task(tmp_path)
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["python -m pytest passed"],
        updated_at="2026-07-01",
    )
    stale_snapshot = read_yaml_with_version(task_yaml)
    write_yaml_atomic(task_yaml, {**stale_snapshot.data, "updated_at": "2026-07-02T09:00:00+08:00"})

    def read_stale_snapshot(path: Path):
        if path == task_yaml:
            return stale_snapshot
        return read_yaml_with_version(path)

    monkeypatch.setattr(validation_module, "read_yaml_with_version", read_stale_snapshot)

    with pytest.raises(WorkbenchError) as exc_info:
        apply_validation(
            tmp_path,
            task_id="REQ-20260702-001-TASK-20260702-001",
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            status="passed",
        )

    assert exc_info.value.code is ErrorCode.CONCURRENT_UPDATE


def test_apply_validation_rejects_missing_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        apply_validation(
            tmp_path,
            task_id="REQ-20260702-001-TASK-20260702-001",
            evidence_id="EV-MISSING",
            status="passed",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_evidence_record: EV-MISSING" in exc_info.value.message


def test_apply_validation_rejects_wrong_task_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "TASK-OTHER",
                "conclusion": "passed",
                "key_outputs": ["pytest passed"],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        apply_validation(
            tmp_path,
            task_id="REQ-20260702-001-TASK-20260702-001",
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            status="passed",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "evidence_task_mismatch" in exc_info.value.message


def test_apply_validation_rejects_passed_with_unverified_items(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        unverified_items=["manual acceptance"],
        updated_at="2026-07-01",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        apply_validation(
            tmp_path,
            task_id="REQ-20260702-001-TASK-20260702-001",
            evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
            status="passed",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "evidence_has_unverified_items" in exc_info.value.message


def test_handoff_status_updates_task_without_changing_validation(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, validation={"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"})

    result = set_handoff_status(
        tmp_path,
        task_id="REQ-20260702-001-TASK-20260702-001",
        status="waiting_user_validation",
        note="等待用户本地验收。",
    )

    task = read_task(tmp_path)
    assert tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml" in result.paths
    assert task["validation"]["status"] == "passed"
    assert task["handoff"] == {
        "status": "waiting_user_validation",
        "note": "等待用户本地验收。",
    }


def test_handoff_status_rejects_stale_task_yaml_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    task_yaml = write_task(tmp_path)
    stale_snapshot = read_yaml_with_version(task_yaml)
    write_yaml_atomic(task_yaml, {**stale_snapshot.data, "updated_at": "2026-07-02T09:00:00+08:00"})

    def read_stale_snapshot(path: Path):
        if path == task_yaml:
            return stale_snapshot
        return read_yaml_with_version(path)

    monkeypatch.setattr(validation_module, "read_yaml_with_version", read_stale_snapshot)

    with pytest.raises(WorkbenchError) as exc_info:
        set_handoff_status(
            tmp_path,
            task_id="REQ-20260702-001-TASK-20260702-001",
            status="waiting_user_validation",
            note="等待用户本地验收。",
        )

    assert exc_info.value.code is ErrorCode.CONCURRENT_UPDATE


@pytest.mark.parametrize("status", ["accepted", "rejected"])
def test_handoff_terminal_status_requires_note(tmp_path: Path, status: str) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        set_handoff_status(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", status=status)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert f"missing_handoff_note: {status}" in exc_info.value.message


def test_done_stage_requires_real_evidence_record_not_just_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        validation={"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in exc_info.value.message


def test_done_stage_rejects_task_yaml_id_mismatch(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        id="REQ-20260702-001-TASK-20260702-999",
        validation={"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-999"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )
    other_dir = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-999"
    other_dir.mkdir(parents=True)
    (other_dir / "evidence.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "EV-REQ-20260702-001-TASK-20260702-999",
                "task_id": "REQ-20260702-001-TASK-20260702-999",
                "conclusion": "passed",
                "key_outputs": ["pytest passed"],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "task_id_mismatch: expected=REQ-20260702-001-TASK-20260702-001 actual=REQ-20260702-001-TASK-20260702-999" in exc_info.value.message


@pytest.mark.parametrize("bad_ref", [".", "../x"])
def test_done_stage_rejects_invalid_evidence_ref(tmp_path: Path, bad_ref: str) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        validation={"status": "passed", "evidence_ref": bad_ref},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": bad_ref,
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": "passed",
                "key_outputs": ["pytest passed"],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert f"invalid_package_ref: {bad_ref}" in exc_info.value.message


@pytest.mark.parametrize("conclusion", ["partial", "closed_with_exception"])
def test_done_stage_rejects_non_passed_validation_conclusions(
    tmp_path: Path,
    conclusion: str,
) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        validation={"status": conclusion, "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": conclusion,
                "key_outputs": ["pytest completed"],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "validation_not_passed" in exc_info.value.message


def test_done_stage_rejects_handoff_rejected(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, handoff={"status": "rejected", "note": "用户验收未通过。"})
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        updated_at="2026-07-01",
    )
    apply_validation(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", evidence_id="EV-REQ-20260702-001-TASK-20260702-001", status="passed")

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "handoff_rejected" in exc_info.value.message


def test_done_stage_rejects_action_note_shape_as_evidence_yaml(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        validation={"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "title": "一次性动作",
                "summary": "这不是 evidence。",
                "related_task_id": "REQ-20260702-001-TASK-20260702-001",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "invalid_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in exc_info.value.message


def test_done_stage_rejects_suspicion_shape_as_evidence_yaml(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        validation={"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "title": "记录疑点",
                "updated_at": "2026-07-01",
                "location_or_subject": "src/demo.py",
                "confirmed_facts": ["发现不一致现象。"],
                "ai_inferences": ["可能需要后续复核。"],
                "current_task_impact": "不影响当前任务。",
                "suggested_handling": "后续单独评估。",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "invalid_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in exc_info.value.message


def test_done_stage_accepts_passed_validation_real_evidence_and_resolved_handoff(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, handoff={"status": "accepted", "note": "用户验收通过。"})
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        updated_at="2026-07-01",
    )
    apply_validation(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", evidence_id="EV-REQ-20260702-001-TASK-20260702-001", status="passed")

    result = set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml" in result.paths
    assert read_task(tmp_path)["stage"] == "done"


def test_done_stage_rejects_accepted_handoff_without_note(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, handoff={"status": "accepted"})
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        updated_at="2026-07-01",
    )
    apply_validation(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", evidence_id="EV-REQ-20260702-001-TASK-20260702-001", status="passed")

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_handoff_note" in exc_info.value.message


def test_done_stage_blocks_waiting_handoff_even_with_real_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, handoff={"status": "waiting_user_validation"})
    create_evidence_record(
        tmp_path,
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        updated_at="2026-07-01",
    )
    apply_validation(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", evidence_id="EV-REQ-20260702-001-TASK-20260702-001", status="passed")

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "REQ-20260702-001-TASK-20260702-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "handoff_waiting" in exc_info.value.message
