from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from codex_workbench.archive import archive_version, plan_version_archive
from codex_workbench.errors import ErrorCode, WorkbenchError


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "0.1", "services": []},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_closed_requirement(root: Path, *, confirmations: list[dict] | None = None) -> None:
    write_yaml(
        root / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001",
            "title": "完成 Workbench 版本",
            "goal": "形成可归档的本地版本。",
            "created_at": "2026-07-01T09:00:00+08:00",
            "updated_at": "2026-07-01T09:00:00+08:00",
            "readiness": {"status": "readable", "confirmed_by_user": True},
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
            "confirmations": confirmations
            if confirmations is not None
            else [
                {
                    "type": "requirement_closure",
                    "source": "user",
                    "note": "用户确认需求已关闭。",
                }
            ],
        },
    )
    (root / "docs" / "active" / "REQ-20260702-001" / "requirement.md").write_text(
        "# REQ-20260702-001\n",
        encoding="utf-8",
    )


def write_done_task(
    root: Path,
    *,
    stage: str = "done",
    obsolete_reason: str | None = None,
    validation: dict | None = None,
    handoff: dict | None = None,
    evidence_conclusion: str = "passed",
    evidence_unverified_items: list[str] | None = None,
) -> None:
    validation_payload = validation or {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
        "unverified_items": [],
    }
    evidence_unverified_items = evidence_unverified_items or []
    task_payload = {
        "schema_version": "0.1",
        "id": "REQ-20260702-001-TASK-20260702-001",
        "requirement_id": "REQ-20260702-001",
        "title": "完成归档前验证",
        "created_at": "2026-07-01T09:30:00+08:00",
        "updated_at": "2026-07-01T10:00:00+08:00",
        "stage": stage,
        "process_level": "standard",
        "risk_level": "standard",
        "validation": validation_payload,
        "handoff": handoff or {"status": "accepted", "note": "用户验收通过。"},
    }
    if obsolete_reason is not None:
        task_payload["obsolete_reason"] = obsolete_reason
    write_yaml(root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml", task_payload)
    (root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.md").write_text(
        "# REQ-20260702-001-TASK-20260702-001\n",
        encoding="utf-8",
    )
    write_yaml(
        root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml",
        {
            "schema_version": "0.1",
            "id": "EV-REQ-20260702-001-TASK-20260702-001",
            "task_id": "REQ-20260702-001-TASK-20260702-001",
            "conclusion": evidence_conclusion,
            "key_outputs": ["python -m pytest passed"],
            "unverified_items": evidence_unverified_items,
        },
    )
    (root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.md").write_text(
        "# EV-REQ-20260702-001-TASK-20260702-001\n",
        encoding="utf-8",
    )


def test_plan_version_archive_requires_independent_archive_authorization(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_archive_authorization" in exc_info.value.message


def test_plan_version_archive_requires_requirement_closure_confirmation(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path, confirmations=[])
    write_done_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_requirement_closure: REQ-20260702-001" in exc_info.value.message


def test_plan_version_archive_blocks_waiting_handoff(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path, handoff={"status": "waiting_user_validation"})

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "archive_preflight_blocked: REQ-20260702-001-TASK-20260702-001 handoff_waiting" in exc_info.value.message


@pytest.mark.parametrize(
    ("validation", "evidence_conclusion", "evidence_unverified_items", "expected"),
    [
        (
            {"status": "failed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001", "unverified_items": []},
            "failed",
            [],
            "validation_not_passed",
        ),
        (
            {
                "status": "passed",
                "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
                "unverified_items": ["manual check"],
            },
            "passed",
            ["manual check"],
            "unverified_items_present",
        ),
    ],
)
def test_plan_version_archive_blocks_incomplete_validation(
    tmp_path: Path,
    validation: dict,
    evidence_conclusion: str,
    evidence_unverified_items: list[str],
    expected: str,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(
        tmp_path,
        validation=validation,
        evidence_conclusion=evidence_conclusion,
        evidence_unverified_items=evidence_unverified_items,
    )

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert expected in exc_info.value.message


def test_plan_version_archive_blocks_missing_evidence_file(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)
    (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml").unlink()

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in exc_info.value.message


def test_plan_version_archive_blocks_rejected_handoff(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path, handoff={"status": "rejected", "note": "用户拒绝验收。"})

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "handoff_rejected" in exc_info.value.message


def test_plan_version_archive_blocks_task_not_closed(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path, stage="in_progress")

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "task_not_closed" in exc_info.value.message


def test_plan_version_archive_allows_obsolete_task_without_done_evidence(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(
        tmp_path,
        stage="obsolete",
        obsolete_reason="任务已废弃，允许随需求归档。",
        validation={"status": "not_started"},
        handoff={"status": "not_required"},
    )

    plan = plan_version_archive(
        tmp_path,
        version="1.0.0",
        requirement_ids=["REQ-20260702-001"],
        archive_authorization_note="用户确认版本可以归档。",
        archived_at="2026-07-01",
    )

    assert {entry.source_id for entry in plan.entries} == {"REQ-20260702-001", "REQ-20260702-001-TASK-20260702-001"}


def test_plan_version_archive_rejects_obsolete_task_without_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(
        tmp_path,
        stage="obsolete",
        validation={"status": "not_started"},
        handoff={"status": "not_required"},
    )

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_obsolete_reason" in exc_info.value.message


@pytest.mark.parametrize("bad_version", [".", "..", "../1.0.0", "1/0/0", " 1.0.0"])
def test_plan_version_archive_rejects_version_path_escape(
    tmp_path: Path,
    bad_version: str,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version=bad_version,
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert f"invalid_archive_version: {bad_version}" in exc_info.value.message


def test_plan_version_archive_rejects_dotdot_requirement_id(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=[".."],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "invalid_package_ref: .." in exc_info.value.message


def test_plan_version_archive_rejects_duplicate_sources(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001", "REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "duplicate_archive_source: requirement REQ-20260702-001" in exc_info.value.message


def test_plan_version_archive_rejects_requirement_id_that_looks_like_task_id(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001-TASK-20260702-001",
            "title": "异常同名需求",
            "goal": "验证路径冲突。",
            "readiness": {"status": "readable", "confirmed_by_user": True},
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
            "confirmations": [{"type": "requirement_closure", "source": "user"}],
        },
    )
    write_done_task(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001-TASK-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "invalid_requirement_package: REQ-20260702-001-TASK-20260702-001" in exc_info.value.message


def test_plan_version_archive_rejects_existing_archive_target(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)
    (tmp_path / "docs" / "archive" / "1.0.0" / "REQ-20260702-001").mkdir(parents=True)

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "archive_target_exists: docs/archive/1.0.0/REQ-20260702-001" in exc_info.value.message


def test_plan_version_archive_rejects_non_empty_version_directory_without_manifest(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)
    notes = tmp_path / "docs" / "archive" / "1.0.0" / "notes.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("unrelated\n", encoding="utf-8")

    with pytest.raises(WorkbenchError) as exc_info:
        plan_version_archive(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "archive_version_directory_not_empty: docs/archive/1.0.0" in exc_info.value.message


def test_archive_version_dry_run_does_not_move_or_write_manifest(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)

    result = archive_version(
        tmp_path,
        version="1.0.0",
        requirement_ids=["REQ-20260702-001"],
        archive_authorization_note="用户确认版本可以归档。",
        archived_at="2026-07-01",
        dry_run=True,
    )

    assert result.dry_run is True
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").exists()
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").exists()
    assert not (tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml").exists()


def test_archive_version_moves_closed_requirement_tasks_and_writes_manifest(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)

    result = archive_version(
        tmp_path,
        version="1.0.0",
        requirement_ids=["REQ-20260702-001"],
        archive_authorization_note="用户确认版本可以归档。",
        archived_at="2026-07-01",
    )

    manifest_path = tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert result.dry_run is False
    assert manifest_path in result.paths
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()
    assert (tmp_path / "docs" / "archive" / "1.0.0" / "REQ-20260702-001" / "requirement.yaml").exists()
    assert (tmp_path / "docs" / "archive" / "1.0.0" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").exists()
    assert manifest["version"] == "1.0.0"
    assert manifest["authorization"]["type"] == "archive_authorization"
    assert manifest["authorization"]["note"] == "用户确认版本可以归档。"
    assert {entry["source_id"] for entry in manifest["entries"]} == {"REQ-20260702-001", "REQ-20260702-001-TASK-20260702-001"}


def test_archive_version_rolls_back_moved_packages_when_move_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    write_closed_requirement(tmp_path)
    write_done_task(tmp_path)
    import codex_workbench.archive as archive_module

    original_move = archive_module.shutil.move
    calls = 0

    def flaky_move(src: str, dst: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated move failure")
        return str(original_move(src, dst))

    monkeypatch.setattr(archive_module.shutil, "move", flaky_move)

    with pytest.raises(WorkbenchError) as exc_info:
        archive_version(
            tmp_path,
            version="1.0.0",
            requirement_ids=["REQ-20260702-001"],
            archive_authorization_note="用户确认版本可以归档。",
            archived_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.IO_ERROR
    assert "archive_write_failed" in exc_info.value.message
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").exists()
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").exists()
    assert not (tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml").exists()
