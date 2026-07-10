from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_task_via_cli,
    create_workspace,
    runner,
    write_requirement,
)


def test_evidence_validation_handoff_commands_allow_done(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    evidence_result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    validation_result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    handoff_result = runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "accepted",
            "--note",
            "用户本地验收通过。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    done_result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text("utf-8")
    )
    assert evidence_result.exit_code == 0
    assert (
        "created docs/active/REQ-20260702-001-TASK-20260702-001/evidence.yaml"
        in evidence_result.output
    )
    assert validation_result.exit_code == 0
    assert (
        "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml"
        in validation_result.output
    )
    assert handoff_result.exit_code == 0
    assert done_result.exit_code == 0
    assert task["stage"] == "done"


def test_evidence_create_dry_run_does_not_write_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/evidence.yaml" in result.output
    assert not (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    ).exists()


def test_evidence_create_requires_explicit_conclusion(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "--conclusion" in combined_output(result)


def test_validation_apply_rejects_missing_evidence_command(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-MISSING",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_evidence_record: EV-MISSING" in combined_output(result)


def test_validation_apply_rejects_status_mismatch(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "failed",
            "--key-output",
            "pytest failed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "validation_status_mismatch" in combined_output(result)


def test_validation_apply_rejects_passed_evidence_with_unverified_items(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "pytest passed",
            "--unverified-item",
            "用户验收未完成。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "evidence_has_unverified_items" in combined_output(result)


def test_done_rechecks_evidence_conclusion_even_if_task_validation_claims_passed(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    evidence_yaml = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    )
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": "failed",
                "key_outputs": ["pytest failed"],
                "unverified_items": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["validation"] = {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
        "unverified_items": [],
    }
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(
        yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "evidence_not_passed: failed" in combined_output(result)


def test_validation_apply_requires_explicit_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "--status" in combined_output(result)


def test_validation_apply_dry_run_does_not_update_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text("utf-8")
    )
    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert task["validation"]["status"] == "not_started"


def test_handoff_set_dry_run_does_not_update_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "waiting_user_validation",
            "--note",
            "等待用户验收。",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text("utf-8")
    )
    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert "handoff" not in task


def test_handoff_waiting_blocks_done_command(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "waiting_user_validation",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "handoff_waiting" in combined_output(result)
