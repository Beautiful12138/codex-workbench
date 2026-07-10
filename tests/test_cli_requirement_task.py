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


def test_requirement_create_command_writes_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "requirement",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code == 0
    assert "created docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert_markdown_template_hint(result.output)
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").exists()


def test_requirement_create_can_auto_id_and_default_time(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T10:30:00+08:00",
    )

    result = runner.invoke(
        app,
        [
            "requirement",
            "create",
            "--title",
            "自动编号需求",
            "--goal",
            "省略 ID 和更新时间也能创建需求。",
            "--acceptance",
            "生成下一个当天需求 ID。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-002" / "requirement.yaml"
    assert result.exit_code == 0, combined_output(result)
    assert "created docs/active/REQ-20260702-002/requirement.yaml" in result.output
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert requirement["id"] == "REQ-20260702-002"
    assert requirement["created_at"] == "2026-07-02T10:30:00+08:00"
    assert requirement["updated_at"] == "2026-07-02T10:30:00+08:00"


def test_task_create_command_writes_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
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
            "--service-ref",
            "codex-workbench",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code == 0
    assert "created docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert "updated docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert_markdown_template_hint(result.output)
    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    task_md = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.md"
    ).read_text(encoding="utf-8")
    assert task_yaml["next_step"] == "运行测试。"
    assert task_yaml["service_refs"] == ["codex-workbench"]
    assert "创建任务包。" not in task_md
    assert "运行测试。" not in task_md


def test_task_create_writes_impact_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "调整本地 SQL",
            "--user-goal",
            "调整本地测试 SQL。",
            "--done",
            "本地测试通过。",
            "--next",
            "准备实现。",
            "--impact-action",
            "code_change",
            "--impact-component",
            "sql",
            "--impact-component",
            "database",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )

    assert result.exit_code == 0, combined_output(result)
    assert task_yaml["impact_profile"]["action"] == "code_change"
    assert task_yaml["impact_profile"]["component_signals"] == ["sql", "database"]
    assert task_yaml["impact_profile"]["contract_change"] is False
    assert task_yaml["impact_profile"]["verification_confidence"] == "local_testable"


def test_task_create_accepts_test_impact_environment(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "code_change",
            "--impact-component",
            "frontend",
            "--impact-environment",
            "test",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
        ],
    )

    assert result.exit_code == 0, combined_output(result)
    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    assert task_yaml["impact_profile"]["environment"] == "test"


def test_task_impact_set_updates_profile_and_records_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    result = runner.invoke(
        app,
        [
            "task",
            "impact-set",
            "REQ-20260702-001-TASK-20260702-001",
            "--risk-level",
            "standard",
            "--process-level",
            "lightweight",
            "--impact-action",
            "code_change",
            "--impact-component",
            "sql",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--risk-trigger",
            "发现真实数据写入时暂停确认。",
            "--reason",
            "读代码后确认只是本地 SQL 查询调整。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    current_text = (tmp_path / "CURRENT.md").read_text(encoding="utf-8")
    index_text = (tmp_path / "docs" / "generated" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, combined_output(result)
    assert task["risk_level"] == "standard"
    assert task["process_level"] == "lightweight"
    assert task["impact_profile"]["action"] == "code_change"
    assert task["impact_profile"]["component_signals"] == ["sql"]
    assert task["risk_triggers"] == ["发现真实数据写入时暂停确认。"]
    assert task["risk_assessment_notes"] == ["读代码后确认只是本地 SQL 查询调整。"]
    assert "实现任务 CLI" in current_text
    assert "standard/lightweight" not in current_text
    assert "code_change local data=none" not in current_text
    assert "standard/lightweight" in index_text
    assert "code_change local data=none" in index_text


def test_task_impact_set_requires_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    result = runner.invoke(
        app,
        [
            "task",
            "impact-set",
            "REQ-20260702-001-TASK-20260702-001",
            "--risk-level",
            "standard",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_risk_assessment_reason" in combined_output(result)


def test_task_check_blocks_low_micro_real_data_write_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "data_write",
            "--impact-component",
            "sql",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "hard",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
        ],
    )
    assert created.exit_code == 0, combined_output(created)
    prepared = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/demo.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    assert prepared.exit_code == 0, combined_output(prepared)

    check = runner.invoke(
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

    assert check.exit_code != 0
    output = combined_output(check)
    assert "impact_profile_requires_risk_escalation" in output
    assert "impact_profile_requires_process_escalation" in output


def test_task_create_can_auto_id_and_default_time(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    existing = create_task_via_cli(tmp_path)
    assert existing.exit_code == 0, combined_output(existing)
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T10:45:00+08:00",
    )

    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "自动编号任务",
            "--user-goal",
            "省略 task ID 和更新时间也能创建任务。",
            "--done",
            "生成所属需求下的下一个当天任务 ID。",
            "--next",
            "继续准备任务。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_id = "REQ-20260702-001-TASK-20260702-002"
    task_yaml = tmp_path / "docs" / "active" / task_id / "task.yaml"
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    assert result.exit_code == 0, combined_output(result)
    assert f"created docs/active/{task_id}/task.yaml" in result.output
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert task["id"] == task_id
    assert task["created_at"] == "2026-07-02T10:45:00+08:00"
    assert task["updated_at"] == "2026-07-02T10:45:00+08:00"
    assert requirement["task_refs"] == [
        "REQ-20260702-001-TASK-20260702-001",
        task_id,
    ]


def test_task_create_refreshes_current_index_and_recovery(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_via_cli(tmp_path)

    assert result.exit_code == 0, combined_output(result)
    current_text = (tmp_path / "CURRENT.md").read_text(encoding="utf-8")
    index_text = (tmp_path / "docs" / "generated" / "index.md").read_text(encoding="utf-8")
    recovery_text = (tmp_path / "docs" / "generated" / "recovery.md").read_text(encoding="utf-8")
    assert "REQ-20260702-001-TASK-20260702-001" in current_text
    assert "REQ-20260702-001-TASK-20260702-001" in index_text
    assert "REQ-20260702-001-TASK-20260702-001" in recovery_text


def test_task_create_dry_run_does_not_write_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
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
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_done_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "final_stage_not_allowed" in combined_output(result)


def test_task_create_rejects_missing_requirement_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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

    assert result.exit_code != 0
    assert "missing_requirement_package: REQ-20260702-001" in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_unconfirmed_requirement_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path, status="intake_draft", confirmed_by_user=False)

    result = runner.invoke(
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

    assert result.exit_code != 0
    output = combined_output(result)
    assert "requirement_not_readable" in output
    assert "missing_user_confirmation" in output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_guarded_initial_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "initial_stage_not_allowed" in combined_output(result)


def test_task_update_packet_preserves_body(tmp_path: Path) -> None:
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
            "update-packet",
            "REQ-20260702-001-TASK-20260702-001",
            "--next",
            "继续实现 CLI。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    task_text = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.md"
    ).read_text(encoding="utf-8")
    assert task_yaml["next_step"] == "继续实现 CLI。"
    assert "## 用户目标" in task_text
    assert "## Current Packet" not in task_text


def test_task_update_packet_rejects_missing_next_step(tmp_path: Path) -> None:
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
            "update-packet",
            "REQ-20260702-001-TASK-20260702-001",
            "--next",
            " ",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_next_step" in combined_output(result)


def test_task_set_stage_rejects_done_without_evidence(tmp_path: Path) -> None:
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
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "stage_transition_blocked" in combined_output(result)


def test_task_prepare_command_allows_in_progress_without_handwritten_yaml(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    before_prepare = runner.invoke(
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
            "--likely-touchpoint",
            "src/codex_workbench/packages.py",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    in_progress = runner.invoke(
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

    task = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )
    assert before_prepare.exit_code != 0
    assert "missing_implementation_ready" in combined_output(before_prepare)
    assert prepare.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in prepare.output
    assert in_progress.exit_code == 0
    assert task["stage"] == "in_progress"
    assert task["implementation"]["ready"] is True
    assert task["implementation"]["conclusion"] == "scoped"
    assert task["working_scope"] == ["src/codex_workbench/cli.py"]
    assert task["risk_triggers"] == ["触发真实数据写入时暂停确认。"]


def test_task_prepare_can_update_impact_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--risk-level",
            "standard",
            "--process-level",
            "standard",
            "--impact-action",
            "code_change",
            "--impact-component",
            "config",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--impact-reason",
            "准备实现时确认只影响本地配置。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )

    assert prepare.exit_code == 0, combined_output(prepare)
    assert task_yaml["risk_level"] == "standard"
    assert task_yaml["process_level"] == "standard"
    assert task_yaml["impact_profile"]["component_signals"] == ["config"]
    assert task_yaml["risk_assessment_notes"] == ["准备实现时确认只影响本地配置。"]


def test_task_prepare_merges_partial_impact_profile_update(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "analysis",
            "--impact-component",
            "api",
            "--impact-environment",
            "test",
            "--impact-data-effect",
            "read_only",
            "--impact-external-effect",
            "read_only",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "easy_manual",
            "--impact-contract-change",
            "unknown",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
        ],
    )
    assert created.exit_code == 0, combined_output(created)

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "projects/customer-api",
            "--impact-contract-change",
            "false",
            "--impact-reason",
            "准备实现时确认不改变接口契约。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = yaml.safe_load(
        (
            tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
        ).read_text(encoding="utf-8")
    )

    assert prepare.exit_code == 0, combined_output(prepare)
    assert task_yaml["impact_profile"] == {
        "action": "analysis",
        "component_signals": ["api"],
        "environment": "test",
        "data_effect": "read_only",
        "external_effect": "read_only",
        "blast_radius": "single_service",
        "reversibility": "easy_manual",
        "contract_change": False,
        "security_or_permission": False,
        "verification_confidence": "integration_required",
    }
    assert task_yaml["risk_assessment_notes"] == ["准备实现时确认不改变接口契约。"]
