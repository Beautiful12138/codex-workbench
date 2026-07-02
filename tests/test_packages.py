from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.models import RequirementState, TaskState
from codex_workbench.packages import (
    block_task,
    create_task_implementation_document,
    create_requirement_package,
    create_task_review_document,
    create_task_package,
    obsolete_task,
    prepare_task,
    set_task_stage,
    update_task_packet,
)
from codex_workbench.templates import RequirementTemplateContext, TaskTemplateContext


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )


def requirement_context() -> RequirementTemplateContext:
    return RequirementTemplateContext(
        requirement_id="REQ-001",
        title="构建轻量 Workbench",
        goal="让 Codex 专注用户任务。",
        acceptance=["可以创建任务包。"],
        non_goals=["不生成厚思想文档。"],
        updated_at="2026-07-01",
    )


def write_requirement(
    root: Path,
    *,
    status: str = "readable",
    confirmed_by_user: bool = True,
) -> None:
    requirement_dir = root / "docs" / "active" / "REQ-001"
    requirement_dir.mkdir(parents=True)
    payload = {
        "schema_version": "0.1",
        "id": "REQ-001",
        "title": "构建轻量 Workbench",
        "goal": "让 Codex 专注用户任务。",
        "acceptance": ["可以创建任务包。"],
        "readiness": {
            "status": status,
            "confirmed_by_user": confirmed_by_user,
        },
    }
    (requirement_dir / "requirement.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_service(root: Path, name: str = "codex-workbench") -> None:
    (root / "services" / "registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "services": [{"name": name, "local_path": str(root), "purpose": "测试服务"}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def task_context(**overrides: object) -> TaskTemplateContext:
    data: dict[str, object] = {
        "task_id": "TASK-001",
        "title": "实现任务 CLI",
        "requirement_id": "REQ-001",
        "user_goal": "创建任务包。",
        "done_means": ["task.yaml 可校验。"],
        "allowed_scope": ["创建 package。"],
        "not_allowed_scope": ["创建 evidence。"],
        "current_next_step": "运行测试。",
        "updated_at": "2026-07-01",
        "service_refs": ["codex-workbench"],
    }
    data.update(overrides)
    return TaskTemplateContext(**data)


def test_create_requirement_package_writes_schema_valid_files(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = create_requirement_package(tmp_path, requirement_context())

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-001" / "requirement.yaml"
    requirement_md = tmp_path / "docs" / "active" / "REQ-001" / "requirement.md"

    assert result.dry_run is False
    assert requirement_yaml in result.paths
    assert requirement_md in result.paths
    RequirementState.model_validate(yaml.safe_load(requirement_yaml.read_text(encoding="utf-8")))
    assert "## 目标" in requirement_md.read_text(encoding="utf-8")


def test_create_task_package_writes_schema_valid_files_without_empty_ceremony(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_package(tmp_path, task_context())

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    task_md = tmp_path / "docs" / "active" / "TASK-001" / "task.md"

    assert task_yaml in result.paths
    assert task_md in result.paths
    TaskState.model_validate(yaml.safe_load(task_yaml.read_text(encoding="utf-8")))
    task_text = task_md.read_text(encoding="utf-8")
    assert "## 用户目标" in task_text
    assert "Review" not in task_text
    assert "Evidence" not in task_text


def test_package_create_dry_run_does_not_write_files(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_package(tmp_path, task_context(), dry_run=True)
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))

    assert result.dry_run is True
    assert result.paths
    assert not (tmp_path / "docs" / "active" / "TASK-001").exists()
    assert "task_refs" not in requirement


def test_create_task_package_rejects_requirement_id_mismatch_without_orphan_task(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-001" / "requirement.yaml"
    data = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    data["id"] = "REQ-OTHER"
    requirement_yaml.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "requirement_id_mismatch: expected=REQ-001 actual=REQ-OTHER" in exc_info.value.message
    assert not (tmp_path / "docs" / "active" / "TASK-001").exists()


def test_create_task_package_rejects_bad_requirement_task_refs_without_orphan_task(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-001" / "requirement.yaml"
    data = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    data["task_refs"] = "TASK-OLD"
    requirement_yaml.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert not (tmp_path / "docs" / "active" / "TASK-001").exists()


def test_package_create_refuses_to_overwrite_existing_files(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "already_exists" in exc_info.value.message


def test_package_paths_cannot_escape_workspace(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    bad_context = task_context(task_id="../TASK-outside")

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, bad_context)

    assert exc_info.value.code is ErrorCode.PATH_OUTSIDE_WORKSPACE


def test_task_create_rejects_direct_done_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context(stage="done"))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "final_stage_not_allowed" in exc_info.value.message


def test_create_task_package_requires_existing_requirement(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_requirement_package: REQ-001" in exc_info.value.message
    assert not (tmp_path / "docs" / "active" / "TASK-001").exists()


def test_create_task_package_requires_readable_requirement(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path, status="intake_draft", confirmed_by_user=False)

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "requirement_not_readable" in exc_info.value.message
    assert "missing_user_confirmation" in exc_info.value.message
    assert not (tmp_path / "docs" / "active" / "TASK-001").exists()


@pytest.mark.parametrize("stage", ["in_progress", "blocked"])
def test_task_create_rejects_guarded_initial_stages(tmp_path: Path, stage: str) -> None:
    create_workspace(tmp_path)

    with pytest.raises(WorkbenchError) as exc_info:
        create_task_package(tmp_path, task_context(stage=stage))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "initial_stage_not_allowed" in exc_info.value.message


def test_update_task_packet_updates_yaml_next_step_only(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    result = update_task_packet(
        tmp_path,
        "TASK-001",
        next_step="继续实现 CLI。",
    )

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    task_md = tmp_path / "docs" / "active" / "TASK-001" / "task.md"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task_text = task_md.read_text(encoding="utf-8")

    assert task_yaml in result.paths
    assert task["next_step"] == "继续实现 CLI。"
    assert "## 用户目标" in task_text
    assert "## Current Packet" not in task_text
    assert "继续实现 CLI。" not in task_text


def test_update_task_packet_rejects_empty_next_step(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    with pytest.raises(WorkbenchError) as exc_info:
        update_task_packet(tmp_path, "TASK-001", next_step=" ")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_next_step" in exc_info.value.message


def test_set_task_stage_updates_yaml_but_rejects_done_without_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    ready_result = set_task_stage(tmp_path, "TASK-001", "ready")
    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"

    assert task_yaml in ready_result.paths
    assert yaml.safe_load(task_yaml.read_text(encoding="utf-8"))["stage"] == "ready"

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "TASK-001", "done")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "stage_transition_blocked" in exc_info.value.message


def test_prepare_task_writes_implementation_ready_state(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context(service_refs=[]))

    result = prepare_task(
        tmp_path,
        "TASK-001",
        working_scope=["src/codex_workbench/packages.py"],
        implementation_ref="implementation.md",
        likely_touchpoints=["src/codex_workbench/cli.py"],
        risk_triggers=["触发真实数据写入时暂停确认。"],
    )

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))

    assert task_yaml in result.paths
    assert task["implementation"] == {
        "ready": True,
        "conclusion": "scoped",
        "ref": "implementation.md",
    }
    assert task["working_scope"] == ["src/codex_workbench/packages.py"]
    assert task["likely_touchpoints"] == ["src/codex_workbench/cli.py"]
    assert task["risk_triggers"] == ["触发真实数据写入时暂停确认。"]


def test_create_task_review_and_implementation_documents_are_package_local(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context(service_refs=[]))

    review_result = create_task_review_document(
        tmp_path,
        "TASK-001",
    )
    implementation_result = create_task_implementation_document(
        tmp_path,
        "TASK-001",
    )

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    review_md = tmp_path / "docs" / "active" / "TASK-001" / "review.md"
    implementation_md = tmp_path / "docs" / "active" / "TASK-001" / "implementation.md"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))

    assert review_md in review_result.paths
    assert implementation_md in implementation_result.paths
    assert task["review"] == {"status": "pending", "ref": "review.md"}
    assert task["implementation"]["ref"] == "implementation.md"
    assert TaskState.model_validate(task).implementation.ready is False
    assert "## 风险与暂停点" in review_md.read_text(encoding="utf-8")
    assert "## 验证计划" in implementation_md.read_text(encoding="utf-8")


def test_set_task_stage_in_progress_allows_empty_service_refs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context(service_refs=[]))
    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    data = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    data["stage"] = "ready"
    data["implementation"] = {"ready": True, "conclusion": "scoped"}
    task_yaml.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = set_task_stage(tmp_path, "TASK-001", "in_progress")

    assert task_yaml in result.paths
    assert yaml.safe_load(task_yaml.read_text(encoding="utf-8"))["stage"] == "in_progress"


def test_set_task_stage_in_progress_rejects_unknown_service_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context(service_refs=["missing-service"]))
    prepare_task(tmp_path, "TASK-001", working_scope=["src/demo.py"])

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "TASK-001", "in_progress")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "unknown_service_ref: missing-service" in exc_info.value.message


def test_set_task_stage_in_progress_allows_registered_service_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_service(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context(service_refs=["codex-workbench"]))
    prepare_task(tmp_path, "TASK-001", working_scope=["src/demo.py"])

    result = set_task_stage(tmp_path, "TASK-001", "in_progress")

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    assert task_yaml in result.paths
    assert yaml.safe_load(task_yaml.read_text(encoding="utf-8"))["stage"] == "in_progress"


def test_set_task_stage_rejects_obsolete_without_obsolete_workflow(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    with pytest.raises(WorkbenchError) as exc_info:
        set_task_stage(tmp_path, "TASK-001", "obsolete")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_obsolete_reason" in exc_info.value.message


def test_block_task_writes_recoverable_blocked_state(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    result = block_task(
        tmp_path,
        "TASK-001",
        reason="等待用户确认验收口径。",
        blocked_by="user",
        resume_condition="用户补充验收口径。",
        resume_stage="ready",
    )

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    assert task_yaml in result.paths
    assert task["stage"] == "blocked"
    assert task["blocked"] == {
        "reason": "等待用户确认验收口径。",
        "blocked_by": "user",
        "resume_condition": "用户补充验收口径。",
        "resume_stage": "ready",
    }


def test_obsolete_task_requires_reason_and_sets_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_package(tmp_path, task_context())

    with pytest.raises(WorkbenchError) as exc_info:
        obsolete_task(tmp_path, "TASK-001", reason=" ")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "missing_obsolete_reason" in exc_info.value.message

    result = obsolete_task(tmp_path, "TASK-001", reason="误建任务，降级为废弃。")

    task_yaml = tmp_path / "docs" / "active" / "TASK-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    assert task_yaml in result.paths
    assert task["stage"] == "obsolete"
    assert task["obsolete_reason"] == "误建任务，降级为废弃。"
