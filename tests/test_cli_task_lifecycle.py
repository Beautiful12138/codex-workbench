from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    assert_markdown_template_hint,
    combined_output,
    create_task_via_cli,
    create_workspace,
    runner,
    write_requirement,
)


def test_task_review_and_implementation_create_use_package_local_docs(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    review = runner.invoke(
        app,
        [
            "task",
            "review-create",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    implementation = runner.invoke(
        app,
        [
            "task",
            "implementation-create",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))

    assert review.exit_code == 0
    assert implementation.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/review.md" in review.output
    assert (
        "updated docs/active/REQ-20260702-001-TASK-20260702-001/implementation.md"
        in implementation.output
    )
    assert_markdown_template_hint(review.output)
    assert_markdown_template_hint(implementation.output)
    assert task["review"] == {"status": "pending", "ref": "review.md"}
    assert task["implementation"]["ref"] == "implementation.md"
    review_text = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "review.md"
    ).read_text(encoding="utf-8")
    implementation_text = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "implementation.md"
    ).read_text(encoding="utf-8")
    assert review_text.startswith("# REQ-20260702-001-TASK-20260702-001 评审\n")
    assert "## 风险与暂停点" in review_text
    assert implementation_text.startswith("# REQ-20260702-001-TASK-20260702-001 实现说明\n")
    assert "## 验证计划" in implementation_text


def test_task_check_previews_stage_guard_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_check = task_yaml.read_text(encoding="utf-8")

    blocked = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    assert blocked.exit_code == 1
    assert "task check blocked REQ-20260702-001-TASK-20260702-001 -> in_progress" in blocked.output
    assert "missing_implementation_ready" in blocked.output
    assert task_yaml.read_text(encoding="utf-8") == before_check

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    allowed = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert prepare.exit_code == 0
    assert allowed.exit_code == 0
    assert "task check allowed REQ-20260702-001-TASK-20260702-001 -> in_progress" in allowed.output
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    assert task["stage"] == "draft"


def test_task_prepare_high_risk_requires_review_ref_and_risk_acceptance(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--risk-level", "high"])

    minimal_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    blocked = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    review_only_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--impact-action",
            "data_write",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "backup_restore",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
            "--impact-reason",
            "高风险任务开工前补齐影响面画像。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    blocked_without_independent_review = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    full_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--reviewer",
            "subagent",
            "--review-independent",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--impact-action",
            "data_write",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "backup_restore",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
            "--impact-reason",
            "高风险任务开工前补齐影响面画像。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    allowed = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert minimal_prepare.exit_code == 0
    assert blocked.exit_code != 0
    output = combined_output(blocked)
    assert "missing_high_risk_review" in output
    assert "missing_high_risk_implementation_ref" in output
    assert "missing_high_risk_triggers" in output
    assert "missing_high_risk_acceptance" in output
    assert review_only_prepare.exit_code == 0
    review_only_output = combined_output(blocked_without_independent_review)
    assert blocked_without_independent_review.exit_code != 0
    assert "missing_high_risk_review_reviewer" in review_only_output
    assert "missing_high_risk_independent_review" in review_only_output
    assert full_prepare.exit_code == 0
    assert allowed.exit_code == 0


def test_high_risk_in_progress_requires_impact_profile_even_when_other_facts_exist(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--risk-level", "high"])
    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--reviewer",
            "subagent",
            "--review-independent",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    blocked = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert prepare.exit_code == 0
    output = combined_output(blocked)
    assert blocked.exit_code != 0
    assert "missing_high_risk_impact_profile" in output
    assert "missing_high_risk_review" not in output
    assert "missing_high_risk_review_reviewer" not in output
    assert "missing_high_risk_independent_review" not in output
    assert "missing_high_risk_implementation_ref" not in output
    assert "missing_high_risk_triggers" not in output
    assert "missing_high_risk_acceptance" not in output


def test_task_set_stage_in_progress_rejects_unknown_service_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
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
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "unknown_service_ref: missing-service" in combined_output(result)


def test_task_check_reports_unknown_service_ref_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_check = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "unknown_service_ref: missing-service" in result.output
    assert task_yaml.read_text(encoding="utf-8") == before_check


def test_task_check_aggregates_lifecycle_and_service_ref_reasons(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "missing_implementation_ready" in result.output
    assert "unknown_service_ref: missing-service" in result.output


def test_task_check_done_reports_missing_evidence_record_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["validation"] = {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
    }
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(
        yaml.safe_dump(task, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    before_check = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "missing_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in result.output
    assert task_yaml.read_text(encoding="utf-8") == before_check


def test_task_block_command_records_resume_condition(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "block",
            "REQ-20260702-001-TASK-20260702-001",
            "--reason",
            "等待用户确认验收。",
            "--blocked-by",
            "user",
            "--resume-condition",
            "用户补充验收口径。",
            "--resume-stage",
            "ready",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert task["stage"] == "blocked"
    assert task["blocked"]["blocked_by"] == "user"
    assert task["blocked"]["resume_condition"] == "用户补充验收口径。"


def test_task_set_stage_rejects_obsolete_without_obsolete_workflow(tmp_path: Path) -> None:
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
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "obsolete",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_obsolete_reason" in combined_output(result)


def test_task_obsolete_command_sets_stage_with_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "obsolete",
            "REQ-20260702-001-TASK-20260702-001",
            "--reason",
            "误建任务，降级为废弃。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert task["stage"] == "obsolete"
    assert task["obsolete_reason"] == "误建任务，降级为废弃。"
