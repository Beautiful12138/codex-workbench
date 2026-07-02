from __future__ import annotations

from pathlib import Path
import tomllib

import pytest
import yaml

from codex_workbench.models import RequirementState, TaskState
from codex_workbench.templates import (
    ActionNoteTemplateContext,
    SuspicionTemplateContext,
    EvidenceTemplateContext,
    RequirementTemplateContext,
    TaskDocumentTemplateContext,
    TaskTemplateContext,
    TemplateError,
    render_action_note,
    render_evidence_document,
    render_implementation_document,
    render_requirement_package,
    render_review_document,
    render_suspicion_log,
    render_task_package,
)


GOLDEN_DIR = Path(__file__).parent / "golden"
WORK_PRODUCT_TEMPLATE_FILES = {
    "action.md",
    "change.md",
    "decision.md",
    "evidence.md",
    "implementation.md",
    "requirement.md",
    "review.md",
    "suspicion.md",
    "task.md",
}


def test_work_product_templates_are_file_based_and_exclude_engineering_docs() -> None:
    root = Path(__file__).resolve().parents[1]
    template_dir = root / "templates" / "work-products"
    actual = {path.name for path in template_dir.glob("*.md")}

    assert actual == WORK_PRODUCT_TEMPLATE_FILES
    assert {"AGENTS.md", "CURRENT.md", "README.md", "WORKSPACE.md"}.isdisjoint(actual)
    assert not any(name.startswith("policy") for name in actual)


def test_wheel_force_include_matches_work_product_template_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert force_include["templates/work-products"] == (
        "codex_workbench/template_files/work-products"
    )


def test_render_task_package_keeps_markdown_skeleton_and_yaml_truth() -> None:
    context = TaskTemplateContext(
        task_id="REQ-20260702-001-TASK-20260702-001",
        title="校准模板体感",
        requirement_id="REQ-20260702-001",
        user_goal="让 Codex 快速进入任务目标。",
        done_means=[
            "第一屏先看到目标、完成口径、范围。",
            "空字段不会生成空章节。",
        ],
        allowed_scope=["渲染任务包 Markdown。", "保持机器状态在 task.yaml。"],
        not_allowed_scope=["生成空 review/development/evidence 章节。", "把思想文档复制进任务包。"],
        current_next_step="先写失败测试。",
        created_at="2026-06-30T09:00:00+08:00",
        updated_at="2026-06-30",
    )

    files = render_task_package(context)

    assert sorted(files) == [
        "docs/active/REQ-20260702-001-TASK-20260702-001/task.md",
        "docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml",
    ]
    assert files["docs/active/REQ-20260702-001-TASK-20260702-001/task.md"] == (
        GOLDEN_DIR / "task" / "REQ-20260702-001-TASK-20260702-001.md"
    ).read_text(encoding="utf-8")
    assert files["docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml"] == (
        GOLDEN_DIR / "task" / "REQ-20260702-001-TASK-20260702-001.yaml"
    ).read_text(encoding="utf-8")
    TaskState.model_validate(yaml.safe_load(files["docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml"]))
    task_yaml = yaml.safe_load(files["docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml"])
    assert task_yaml["process_level"] == "micro"
    assert task_yaml["risk_level"] == "low"
    assert task_yaml["next_step"] == "先写失败测试。"
    assert task_yaml["service_refs"] == []
    markdown = files["docs/active/REQ-20260702-001-TASK-20260702-001/task.md"]
    assert "不要为了模板复述 task.yaml" in markdown
    assert "让 Codex 快速进入任务目标。" not in markdown
    assert "第一屏先看到目标" not in markdown
    assert "渲染任务包 Markdown。" not in markdown
    assert "先写失败测试。" not in markdown
    expected_sections = [
        "## 用户目标",
        "## 完成口径",
        "## 范围",
        "## 非范围",
        "## 服务上下文",
        "## 下一步",
        "## 实现提示",
        "## 验证要求",
        "## 暂停条件",
        "## 备注",
    ]
    assert all(section in markdown for section in expected_sections)
    assert [markdown.index(section) for section in expected_sections] == sorted(
        markdown.index(section) for section in expected_sections
    )


def test_render_task_package_omits_empty_ceremony() -> None:
    files = render_task_package(
        TaskTemplateContext(
            task_id="REQ-20260702-001-TASK-20260702-002",
            title="保持轻量",
            requirement_id="REQ-20260702-001",
            user_goal="验证空字段不污染输出。",
            done_means=["输出不包含空仪式。"],
            allowed_scope=[],
            not_allowed_scope=[],
            current_next_step="继续。",
            created_at="2026-06-30T09:00:00+08:00",
            updated_at="2026-06-30",
        )
    )

    markdown = files["docs/active/REQ-20260702-001-TASK-20260702-002/task.md"]
    yaml_text = files["docs/active/REQ-20260702-001-TASK-20260702-002/task.yaml"]

    assert "Review" not in markdown
    assert "Development" not in markdown
    assert "Evidence" not in markdown
    assert "允许：" not in markdown
    assert "不做：" not in markdown
    assert "None" not in markdown
    assert "next_step: 继续。" in yaml_text
    assert "assumptions: []" not in yaml_text
    assert "questions_for_user: []" not in yaml_text


def test_render_requirement_evidence_and_action_are_minimal_and_stable() -> None:
    requirement = RequirementTemplateContext(
        requirement_id="REQ-20260702-001",
        title="构建轻量 Workbench",
        goal="让 Codex 专注用户任务。",
        acceptance=["模板输出稳定。"],
        created_at="2026-06-30T09:00:00+08:00",
        updated_at="2026-06-30",
    )
    evidence = EvidenceTemplateContext(
        evidence_id="EV-REQ-20260702-001-TASK-20260702-001",
        task_id="REQ-20260702-001-TASK-20260702-001",
        conclusion="passed",
        key_outputs=["pytest passed"],
        updated_at="2026-06-30",
    )
    action = ActionNoteTemplateContext(
        action_id="ACT-001",
        title="登记材料",
        summary="只记录冷路径材料。",
        action_type="maintenance_action",
        related_refs=["REQ-20260702-001-TASK-20260702-001"],
        updated_at="2026-06-30",
    )

    assert render_requirement_package(requirement) == render_requirement_package(requirement)
    assert render_evidence_document(evidence) == render_evidence_document(evidence)
    assert render_action_note(action) == render_action_note(action)

    requirement_md = render_requirement_package(requirement)["docs/active/REQ-20260702-001/requirement.md"]
    requirement_yaml = render_requirement_package(requirement)[
        "docs/active/REQ-20260702-001/requirement.yaml"
    ]
    evidence_md = render_evidence_document(evidence)["docs/active/REQ-20260702-001-TASK-20260702-001/evidence.md"]
    action_md = render_action_note(action)["docs/actions/ACT-001.md"]
    action_yaml = render_action_note(action)["docs/actions/ACT-001.yaml"]

    RequirementState.model_validate(yaml.safe_load(requirement_yaml))
    action_yaml = yaml.safe_load(action_yaml)
    assert "## 目标" in requirement_md
    assert "## 验收标准" in requirement_md
    assert "不要为了模板复述 requirement.yaml" in requirement_md
    assert "让 Codex 专注用户任务。" not in requirement_md
    assert "模板输出稳定。" not in requirement_md
    assert "pytest passed" not in evidence_md
    assert evidence_md.startswith("# EV-REQ-20260702-001-TASK-20260702-001 / task REQ-20260702-001-TASK-20260702-001\n")
    assert "只记录已经发生的任务验证事实" in evidence_md
    assert "action note 不能替代 evidence" in evidence_md
    assert "未验证项" in evidence_md
    assert "验证结论" in evidence_md
    assert action_yaml["summary"] == "只记录冷路径材料。"
    assert action_yaml["status"] == "executed"
    assert action_yaml["related_refs"] == ["REQ-20260702-001-TASK-20260702-001"]
    assert action_md.startswith("# ACT-001 登记材料\n")
    assert "Action Note 只记录非任务动作" in action_md
    assert "不能替代 task evidence" in action_md
    assert "不能支撑 validation.status=passed" in action_md
    assert "## 操作记录" in action_md
    assert "只记录冷路径材料。" not in action_md


def test_record_templates_are_opening_pages_not_forms() -> None:
    action = ActionNoteTemplateContext(
        action_id="ACT-EMPTY",
        title="无关联动作",
        summary="没有关联对象。",
        action_type="maintenance_action",
        updated_at="2026-07-01",
    )
    suspicion = SuspicionTemplateContext(
        suspicion_id="SUS-EMPTY",
        title="无假设疑点",
        updated_at="2026-07-01",
        location_or_subject="src/demo.py",
        confirmed_facts=["发现不一致现象。"],
        ai_inferences=["可能需要后续复核。"],
        current_task_impact="不影响当前任务。",
        suggested_handling="后续单独评估。",
    )

    action_yaml = yaml.safe_load(render_action_note(action)["docs/actions/ACT-EMPTY.yaml"])
    action_md = render_action_note(action)["docs/actions/ACT-EMPTY.md"]
    suspicion_yaml = yaml.safe_load(
        render_suspicion_log(suspicion)["docs/suspicions/SUS-EMPTY.yaml"]
    )
    suspicion_md = render_suspicion_log(suspicion)["docs/suspicions/SUS-EMPTY.md"]

    assert "related_refs" not in action_yaml
    assert "authorization" not in action_yaml
    assert "target" not in action_yaml
    assert "result" not in action_yaml
    assert action_yaml["status"] == "executed"
    assert "assumptions" not in suspicion_yaml
    assert "related_refs" not in suspicion_yaml
    assert action_md.startswith("# ACT-EMPTY 无关联动作\n")
    assert suspicion_md.startswith("# SUS-EMPTY 无假设疑点\n")
    assert "updated_at:" not in action_md
    assert "status:" not in action_md
    assert "没有关联对象。" not in action_md
    assert "不影响当前任务。" not in suspicion_md
    assert "## 不确定点" in suspicion_md


def test_render_package_local_review_and_implementation_documents() -> None:
    context = TaskDocumentTemplateContext(task_id="REQ-20260702-001-TASK-20260702-001")

    review = render_review_document(context)
    implementation = render_implementation_document(context)

    assert sorted(review) == ["docs/active/REQ-20260702-001-TASK-20260702-001/review.md"]
    assert sorted(implementation) == ["docs/active/REQ-20260702-001-TASK-20260702-001/implementation.md"]
    assert "## 风险与暂停点" in review["docs/active/REQ-20260702-001-TASK-20260702-001/review.md"]
    assert "## 验证计划" in implementation["docs/active/REQ-20260702-001-TASK-20260702-001/implementation.md"]


def test_template_context_rejects_empty_required_fields() -> None:
    with pytest.raises(TemplateError):
        TaskTemplateContext(
            task_id="",
            title="缺少 ID",
            requirement_id="REQ-20260702-001",
            user_goal="目标",
            done_means=["完成"],
            current_next_step="下一步",
            created_at="2026-06-30T09:00:00+08:00",
            updated_at="2026-06-30",
        )


def test_action_template_context_rejects_product_task_action_type() -> None:
    with pytest.raises(TemplateError):
        ActionNoteTemplateContext(
            action_id="ACT-BAD",
            title="错误动作类型",
            summary="product_task 应进入正式 task。",
            action_type="product_task",
            updated_at="2026-07-01",
        )


def test_action_template_context_rejects_invalid_status() -> None:
    with pytest.raises(TemplateError):
        ActionNoteTemplateContext(
            action_id="ACT-BAD",
            title="错误动作状态",
            summary="状态必须可枚举。",
            action_type="maintenance_action",
            status="unknown",
            updated_at="2026-07-01",
        )
