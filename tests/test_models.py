from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from codex_workbench import models as model_module
from codex_workbench.models import (
    ActionNoteState,
    ImpactAction,
    ImpactEnvironment,
    HandoffStatus,
    Knowledge,
    ProcessLevel,
    ReviewReviewer,
    ReviewStatus,
    RiskLevel,
    ServiceRegistry,
    RequirementState,
    TaskStage,
    TaskState,
)
from codex_workbench.schema import CURRENT_SCHEMA_VERSION, core_model_json_schemas


ROOT = Path(__file__).resolve().parents[1]


def minimal_task(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "id": "REQ-20260702-001-TASK-20260702-001",
        "requirement_id": "REQ-20260702-001",
        "title": "Demo task",
        "created_at": "2026-07-02T10:00:00+08:00",
        "updated_at": "2026-07-02T10:00:00+08:00",
        "stage": "draft",
        "service_refs": [],
    }
    data.update(overrides)
    return data


def test_task_state_accepts_minimal_valid_task() -> None:
    task = TaskState.model_validate(minimal_task())

    assert task.schema_version == CURRENT_SCHEMA_VERSION
    assert task.stage is TaskStage.DRAFT
    assert task.knowledge.confirmed_facts == []


def test_task_state_accepts_requirement_linked_task_id() -> None:
    task = TaskState.model_validate(
        minimal_task(
            id="REQ-20260702-001-TASK-20260702-001",
            requirement_id="REQ-20260702-001",
        )
    )

    assert task.id == "REQ-20260702-001-TASK-20260702-001"
    assert task.requirement_id == "REQ-20260702-001"


def test_task_state_requires_requirement_id() -> None:
    data = minimal_task()
    data.pop("requirement_id")

    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(data)

    assert exc_info.value.errors()[0]["loc"] == ("requirement_id",)


def test_task_state_rejects_task_id_outside_requirement_prefix() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(
            minimal_task(
                id="REQ-20260703-001-TASK-20260703-001",
                requirement_id="REQ-20260702-001",
            )
        )

    assert "task_id_requirement_prefix_mismatch" in str(exc_info.value)


def test_requirement_state_requires_created_and_updated_time() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RequirementState.model_validate(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "REQ-20260702-001",
                "title": "Demo requirement",
                "goal": "稳定协作。",
                "acceptance": ["有时间字段。"],
                "updated_at": "2026-07-02T10:00:00+08:00",
            }
        )

    assert exc_info.value.errors()[0]["loc"] == ("created_at",)


def test_task_state_requires_created_and_updated_time() -> None:
    data = minimal_task()
    data.pop("updated_at")

    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(data)

    assert exc_info.value.errors()[0]["loc"] == ("updated_at",)


def test_task_state_rejects_non_dated_task_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(
            minimal_task(
                id="REQ-20260702-001-TASK-001",
                requirement_id="REQ-20260702-001",
            )
        )

    assert "invalid_task_id_format" in str(exc_info.value)


def test_task_state_rejects_unknown_stage() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(minimal_task(stage="reviewed"))

    assert exc_info.value.errors()[0]["type"] == "enum"


def test_task_state_rejects_unknown_schema_version() -> None:
    with pytest.raises(ValidationError):
        TaskState.model_validate(minimal_task(schema_version="9.9"))


def test_task_state_requires_schema_version() -> None:
    data = minimal_task()
    data.pop("schema_version")

    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(data)

    assert exc_info.value.errors()[0]["type"] == "missing"


def test_review_status_has_own_done_semantics() -> None:
    task = TaskState.model_validate(
        minimal_task(
            review={
                "status": "done",
                "reviewer": "subagent",
                "independent": True,
            }
        )
    )

    assert task.review.status is ReviewStatus.DONE
    assert task.review.reviewer is ReviewReviewer.SUBAGENT
    assert task.review.independent is True


def test_task_state_accepts_lifecycle_dimensions() -> None:
    task = TaskState.model_validate(
        minimal_task(
            process_level="micro",
            risk_level="low",
            handoff={"status": "waiting_user_validation"},
            obsolete_reason="误建任务，已废弃。",
            next_step="补齐 implementation-ready。",
            working_scope=["task package"],
            likely_touchpoints=["src/codex_workbench"],
            risk_triggers=["触发真实数据写入时暂停确认。"],
            risk_assessment_notes=["用户确认只是本地风险。"],
        )
    )

    assert task.process_level is ProcessLevel.MICRO
    assert task.risk_level is RiskLevel.LOW
    assert task.handoff.status is HandoffStatus.WAITING_USER_VALIDATION
    assert task.obsolete_reason == "误建任务，已废弃。"
    assert task.next_step == "补齐 implementation-ready。"
    assert task.working_scope == ["task package"]
    assert task.likely_touchpoints == ["src/codex_workbench"]
    assert task.risk_triggers == ["触发真实数据写入时暂停确认。"]
    assert task.risk_assessment_notes == ["用户确认只是本地风险。"]


def test_task_state_accepts_impact_profile() -> None:
    task = TaskState.model_validate(
        minimal_task(
            impact_profile={
                "action": "code_change",
                "component_signals": ["sql", "database"],
                "environment": "local",
                "data_effect": "none",
                "external_effect": "none",
                "blast_radius": "single_service",
                "reversibility": "git_revert",
                "contract_change": False,
                "security_or_permission": False,
                "verification_confidence": "local_testable",
            }
        )
    )

    assert task.impact_profile is not None
    assert task.impact_profile.action is ImpactAction.CODE_CHANGE
    assert task.impact_profile.environment is ImpactEnvironment.LOCAL
    assert task.impact_profile.component_signals == ["sql", "database"]
    assert task.impact_profile.contract_change is False


def test_task_state_rejects_invalid_impact_profile_enum() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(
            minimal_task(
                impact_profile={
                    "action": "database",
                    "environment": "local",
                }
            )
        )

    assert exc_info.value.errors()[0]["type"] == "enum"


def test_task_state_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(minimal_task(unexpected=True))

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize("removed_field", ["forbidden_scope"])
def test_task_state_rejects_removed_structured_scope_fields(removed_field: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskState.model_validate(minimal_task(**{removed_field: ["not used in v1"]}))

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"


def test_action_note_state_rejects_product_task_as_action_type() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ActionNoteState.model_validate(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "ACT-001",
                "title": "错误动作类型",
                "updated_at": "2026-07-01",
                "summary": "product_task 不应作为 action note。",
                "action_type": "product_task",
                "side_effect_summary": "no_side_effect",
                "rollback_hint": "no_rollback_needed",
            }
        )

    assert exc_info.value.errors()[0]["type"] == "enum"


def test_action_note_state_accepts_status_and_execution_context() -> None:
    action = ActionNoteState.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "id": "ACT-001",
            "title": "记录动作上下文",
            "updated_at": "2026-07-01",
            "summary": "只记录非任务动作。",
            "action_type": "maintenance_action",
            "status": "partial",
            "authorization": "用户确认。",
            "target": "docs/generated",
            "result": "部分完成。",
            "side_effect_summary": "no_side_effect",
            "rollback_hint": "no_rollback_needed",
        }
    )

    assert action.status.value == "partial"
    assert action.authorization == "用户确认。"
    assert action.target == "docs/generated"
    assert action.result == "部分完成。"


def test_action_note_state_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ActionNoteState.model_validate(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "ACT-001",
                "title": "错误动作状态",
                "updated_at": "2026-07-01",
                "summary": "状态必须可枚举。",
                "action_type": "maintenance_action",
                "status": "unknown",
                "side_effect_summary": "no_side_effect",
                "rollback_hint": "no_rollback_needed",
            }
        )

    assert exc_info.value.errors()[0]["type"] == "enum"


def test_knowledge_lists_are_not_shared() -> None:
    first = Knowledge()
    second = Knowledge()

    first.confirmed_facts.append("用户确认 v1 不做 Web UI")

    assert second.confirmed_facts == []


def test_service_registry_accepts_current_seed_file() -> None:
    registry_data = yaml.safe_load((ROOT / "services" / "registry.yaml").read_text(encoding="utf-8"))

    registry = ServiceRegistry.model_validate(registry_data)

    assert registry.schema_version == CURRENT_SCHEMA_VERSION
    assert registry.services == []


def test_service_registry_rejects_removed_candidate_services_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ServiceRegistry.model_validate(
            {"schema_version": CURRENT_SCHEMA_VERSION, "services": [], "candidate_services": []}
        )

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"


def test_material_registry_model_keeps_raw_materials_in_inbox() -> None:
    assert hasattr(model_module, "MaterialRegistry")
    registry = model_module.MaterialRegistry.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "materials": [
                {
                    "id": "MAT-001",
                    "title": "思想文件",
                    "source": "用户提供的本地 Markdown",
                    "received_at": "2026-07-01",
                    "summary": "描述 Workbench 的材料、发现和 intake 边界。",
                }
            ],
        }
    )

    assert registry.materials[0].committable_original is False


def test_discovery_state_model_separates_observations_and_inferences() -> None:
    assert hasattr(model_module, "DiscoveryState")
    discovery = model_module.DiscoveryState.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "id": "DISC-001",
            "title": "材料边界发现",
            "material_refs": ["MAT-001"],
            "updated_at": "2026-07-01",
            "knowledge": {
                "system_observations": ["inbox 材料尚未成熟。"],
                "ai_inferences": ["需要 intake 确认后才能创建正式任务。"],
            },
        }
    )

    assert discovery.knowledge.system_observations == ["inbox 材料尚未成熟。"]
    assert discovery.knowledge.ai_inferences == ["需要 intake 确认后才能创建正式任务。"]


def test_record_models_cover_change_and_suspicion_minimum_fields() -> None:
    change = model_module.ChangeRecordState.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "id": "CHG-001",
            "title": "记录范围变化",
            "updated_at": "2026-07-01",
            "change_kind": "scope_change",
            "changed_area": "acceptance",
            "reason": "用户改变验收口径。",
            "impact": "需要更新任务边界。",
            "handling": "先记录变更，再继续实现。",
        }
    )
    suspicion = model_module.SuspicionState.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "id": "SUS-001",
            "title": "记录疑点",
            "updated_at": "2026-07-01",
            "location_or_subject": "src/demo.py",
            "confirmed_facts": ["发现不一致现象。"],
            "ai_inferences": ["可能需要后续复核。"],
            "current_task_impact": "不影响当前任务。",
            "suggested_handling": "后续单独评估。",
        }
    )

    assert change.change_kind.value == "scope_change"
    assert suspicion.confirmed_facts == ["发现不一致现象。"]


def test_change_record_state_rejects_implementation_adjustment_as_formal_record() -> None:
    for change_kind in ["implementation_adjustment", "scope_clarification"]:
        with pytest.raises(ValidationError) as exc_info:
            model_module.ChangeRecordState.model_validate(
                {
                    "schema_version": CURRENT_SCHEMA_VERSION,
                    "id": "CHG-001",
                    "title": "局部实现调整",
                    "updated_at": "2026-07-01",
                    "change_kind": change_kind,
                    "changed_area": "copy",
                    "reason": "只改局部文案。",
                    "impact": "不改变验收口径。",
                    "handling": "直接在当前任务内处理。",
                }
            )

        assert "formal_change_record_requires_scope_change" in str(exc_info.value)


def test_change_record_state_rejects_legacy_implementation_adjustment_shape() -> None:
    with pytest.raises(ValidationError) as exc_info:
        model_module.ChangeRecordState.model_validate(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": "CHG-001",
                "title": "局部实现调整",
                "updated_at": "2026-07-01",
                "change_kind": "implementation_adjustment",
                "changed_area": "copy",
                "reason": "只改局部文案。",
                "impact": "不改变验收口径。",
                "handling": "直接在当前任务内处理。",
            }
        )

    assert "formal_change_record_requires_scope_change" in str(exc_info.value)


def test_core_model_json_schemas_can_be_generated() -> None:
    schemas = core_model_json_schemas()

    assert "TaskState" in schemas
    assert "MaterialRegistry" in schemas
    assert "DiscoveryState" in schemas
    assert schemas["TaskState"]["type"] == "object"
    assert "ServiceRegistry" in schemas
