from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_workspace,
    runner,
    write_requirement,
)


def test_action_create_writes_machine_record_and_does_not_touch_task(tmp_path: Path) -> None:
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
            "保持旁路动作独立",
            "--user-goal",
            "动作记录不污染任务状态。",
            "--done",
            "action note 不支撑验证。",
            "--next",
            "创建动作记录。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_task = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录一次辅助动作",
            "--summary",
            "只记录动作，不支撑验证。",
            "--action-type",
            "maintenance_action",
            "--status",
            "partial",
            "--authorization",
            "用户确认本地维护动作。",
            "--target",
            "docs/generated",
            "--result",
            "已完成局部整理。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--side-effect-summary",
            "no_side_effect",
            "--rollback-hint",
            "no_rollback_needed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    action_yaml = tmp_path / "docs" / "actions" / "ACT-001.yaml"
    action_md = tmp_path / "docs" / "actions" / "ACT-001.md"
    assert result.exit_code == 0
    action = yaml.safe_load(action_yaml.read_text(encoding="utf-8"))
    assert "created docs/actions/ACT-001.yaml" in result.output
    assert "created docs/actions/ACT-001.md" in result.output
    assert action["id"] == "ACT-001"
    assert action["summary"] == "只记录动作，不支撑验证。"
    assert action["action_type"] == "maintenance_action"
    assert action["status"] == "partial"
    assert action["authorization"] == "用户确认本地维护动作。"
    assert action["target"] == "docs/generated"
    assert action["result"] == "已完成局部整理。"
    assert action["related_refs"] == ["REQ-20260702-001-TASK-20260702-001"]
    action_md_text = action_md.read_text(encoding="utf-8")
    assert action_md_text.startswith("# ACT-001 记录一次辅助动作\n")
    assert "## 操作记录" in action_md_text
    assert "只记录动作，不支撑验证。" not in action_md_text
    assert task_yaml.read_text(encoding="utf-8") == before_task


def test_action_create_rejects_product_task_action_type(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "错误动作类型",
            "--summary",
            "product_task 应进入正式 task，不应写 action note。",
            "--action-type",
            "product_task",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "validation_error" in combined_output(result)


def test_action_create_accepts_ops_and_ephemeral_action_types(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    for action_id, action_type in [
        ("ACT-OPS", "ops_action"),
        ("ACT-CHECK", "ephemeral_check"),
    ]:
        result = runner.invoke(
            app,
            [
                "action",
                "create",
                action_id,
                "--title",
                "记录非任务动作",
                "--summary",
                "只记录动作，不支撑验证。",
                "--action-type",
                action_type,
                "--workspace-root",
                str(tmp_path),
                "--updated-at",
                "2026-07-01",
            ],
        )

        action_yaml = yaml.safe_load(
            (tmp_path / "docs" / "actions" / f"{action_id}.yaml").read_text(encoding="utf-8")
        )
        assert result.exit_code == 0
        assert action_yaml["action_type"] == action_type
        assert action_yaml["status"] == "executed"


def test_action_create_rejects_invalid_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "错误动作状态",
            "--summary",
            "动作状态必须可枚举。",
            "--action-type",
            "maintenance_action",
            "--status",
            "unknown",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "validation_error" in combined_output(result)


def test_change_classify_keeps_implementation_adjustment_lightweight(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "implementation_adjustment",
            "--summary",
            "只改局部文案。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "implementation_adjustment" in result.output
    assert "no_formal_change_record" in result.output
    assert not (tmp_path / "docs" / "changes").exists()


def test_change_classify_keeps_scope_clarification_lightweight(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "scope_clarification",
            "--summary",
            "用户澄清文案口径，但目标不变。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "scope_clarification" in result.output
    assert "requires_change_record=false" in result.output
    assert "scope_alignment_required" in result.output
    assert not (tmp_path / "docs" / "changes").exists()


def test_change_classify_requires_record_for_scope_change(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "scope_change",
            "--summary",
            "验收口径发生变化。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "scope_change" in result.output
    assert "requires_change_record=true" in result.output
    assert "change_control_required" in result.output


def test_change_create_writes_formal_change_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "create",
            "CHG-001",
            "--title",
            "记录验收变化",
            "--changed-area",
            "acceptance",
            "--reason",
            "用户改变验收口径。",
            "--impact",
            "需要更新任务边界。",
            "--handling",
            "先记录变更，再继续实现。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    change_yaml = tmp_path / "docs" / "changes" / "CHG-001.yaml"
    change_md = tmp_path / "docs" / "changes" / "CHG-001.md"
    assert result.exit_code == 0
    change = yaml.safe_load(change_yaml.read_text(encoding="utf-8"))
    assert "created docs/changes/CHG-001.yaml" in result.output
    assert "created docs/changes/CHG-001.md" in result.output
    assert change["id"] == "CHG-001"
    assert change["change_kind"] == "scope_change"
    assert change["changed_area"] == "acceptance"
    assert change["related_refs"] == ["REQ-20260702-001-TASK-20260702-001"]
    assert change["reason"] == "用户改变验收口径。"
    change_text = change_md.read_text(encoding="utf-8")
    assert change_text.startswith("# CHG-001 记录验收变化\n")
    assert "## 新口径" in change_text
    assert "用户改变验收口径。" not in change_text


def test_decision_create_writes_cold_path_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录工具的机器真源。",
            "--decision",
            "四类记录使用 YAML 作为机器真源。",
            "--impact",
            "后续 CLI 和模板按该口径实现。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    decision_yaml = tmp_path / "docs" / "decisions" / "DEC-001.yaml"
    decision_md = tmp_path / "docs" / "decisions" / "DEC-001.md"
    assert result.exit_code == 0
    decision = yaml.safe_load(decision_yaml.read_text(encoding="utf-8"))
    assert decision["id"] == "DEC-001"
    assert decision["cold_path_reason"] == "影响多个后续任务。"
    assert decision["decision"] == "四类记录使用 YAML 作为机器真源。"
    decision_text = decision_md.read_text(encoding="utf-8")
    assert decision_text.startswith("# DEC-001 记录长期决策\n")
    assert "## 取舍" in decision_text
    assert "影响多个后续任务。" not in decision_text


def test_suspicion_create_records_clue_without_touching_task(tmp_path: Path) -> None:
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
            "保持疑点独立",
            "--user-goal",
            "疑点记录不授权修改。",
            "--done",
            "任务状态不被疑点记录改变。",
            "--next",
            "记录疑点。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_task = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "suspicion",
            "create",
            "SUS-001",
            "--title",
            "记录疑点",
            "--location",
            "src/demo.py",
            "--fact",
            "发现不一致现象。",
            "--inference",
            "可能需要后续复核。",
            "--assumption",
            "当前证据不足以修改。",
            "--current-task-impact",
            "不影响当前任务。",
            "--suggested-handling",
            "后续单独评估。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    suspicion_yaml = tmp_path / "docs" / "suspicions" / "SUS-001.yaml"
    suspicion_md = tmp_path / "docs" / "suspicions" / "SUS-001.md"
    assert result.exit_code == 0
    suspicion = yaml.safe_load(suspicion_yaml.read_text(encoding="utf-8"))
    assert suspicion["id"] == "SUS-001"
    assert suspicion["confirmed_facts"] == ["发现不一致现象。"]
    assert suspicion["ai_inferences"] == ["可能需要后续复核。"]
    assert suspicion["current_task_impact"] == "不影响当前任务。"
    assert suspicion["suggested_handling"] == "后续单独评估。"
    suspicion_text = suspicion_md.read_text(encoding="utf-8")
    assert suspicion_text.startswith("# SUS-001 记录疑点\n")
    assert "## 不确定点" in suspicion_text
    assert "后续单独评估。" not in suspicion_text
    assert task_yaml.read_text(encoding="utf-8") == before_task


def test_action_create_dry_run_duplicate_and_bad_ref_guards(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    dry_run = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )
    assert dry_run.exit_code == 0
    assert "dry-run docs/actions/ACT-001.yaml" in dry_run.output
    assert not (tmp_path / "docs" / "actions" / "ACT-001.yaml").exists()

    created = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    duplicate = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    bad_ref = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-002",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--related-ref",
            "TASK/001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert created.exit_code == 0
    assert duplicate.exit_code != 0
    assert "already_exists: docs/actions/ACT-001.yaml" in combined_output(duplicate)
    assert bad_ref.exit_code != 0
    assert "invalid_package_ref: TASK/001" in combined_output(bad_ref)


def test_change_decision_suspicion_negative_guards(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    change_dry_run = runner.invoke(
        app,
        [
            "change",
            "create",
            "CHG-001",
            "--title",
            "记录范围变化",
            "--changed-area",
            "acceptance",
            "--reason",
            "验收口径变化。",
            "--impact",
            "需要更新任务边界。",
            "--handling",
            "先记录变更再继续。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )
    assert change_dry_run.exit_code == 0
    assert "dry-run docs/changes/CHG-001.yaml" in change_dry_run.output
    assert not (tmp_path / "docs" / "changes" / "CHG-001.yaml").exists()

    decision_create = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录口径。",
            "--decision",
            "采用冷路径记录。",
            "--impact",
            "后续任务复用该口径。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    decision_duplicate = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录口径。",
            "--decision",
            "采用冷路径记录。",
            "--impact",
            "后续任务复用该口径。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    assert decision_create.exit_code == 0
    assert decision_duplicate.exit_code != 0
    assert "already_exists: docs/decisions/DEC-001.yaml" in combined_output(decision_duplicate)

    suspicion_bad_ref = runner.invoke(
        app,
        [
            "suspicion",
            "create",
            "SUS-001",
            "--title",
            "记录疑点",
            "--location",
            "src/demo.py",
            "--fact",
            "发现不一致现象。",
            "--inference",
            "可能需要后续复核。",
            "--current-task-impact",
            "不影响当前任务。",
            "--suggested-handling",
            "后续单独评估。",
            "--related-ref",
            "../REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    assert suspicion_bad_ref.exit_code != 0
    assert "invalid_package_ref: ../REQ-20260702-001-TASK-20260702-001" in combined_output(
        suspicion_bad_ref
    )
