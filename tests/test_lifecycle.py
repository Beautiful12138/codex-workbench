from __future__ import annotations

from codex_workbench.lifecycle import (
    FactSource,
    evaluate_archive_task,
    evaluate_task_transition,
    evaluate_validation_record,
    requirement_allows_formal_task,
    stronger_fact_source,
)
from codex_workbench.models import (
    ActionNoteState,
    EvidenceState,
    RequirementState,
    SuspicionState,
    TaskStage,
    TaskState,
)
from codex_workbench.schema import CURRENT_SCHEMA_VERSION


def task(**overrides: object) -> TaskState:
    data: dict[str, object] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "id": "REQ-20260702-001-TASK-20260702-001",
        "requirement_id": "REQ-20260702-001",
        "title": "Demo lifecycle task",
        "created_at": "2026-07-01T09:00:00+08:00",
        "updated_at": "2026-07-01T09:00:00+08:00",
        "stage": "ready",
        "service_refs": ["app"],
    }
    data.update(overrides)
    return TaskState.model_validate(data)


def test_in_progress_requires_implementation_ready_without_service_whitelist() -> None:
    ready_task = task(
        implementation={"ready": True, "conclusion": "scoped"},
        service_refs=["unknown-service"],
    )

    allowed = evaluate_task_transition(
        ready_task,
        TaskStage.IN_PROGRESS,
    )

    assert allowed.allowed is True
    assert allowed.reason_codes == ()


def test_high_risk_in_progress_rejects_blank_scope_and_triggers() -> None:
    blank_ready_high_task = task(
        risk_level="high",
        implementation={
            "ready": True,
            "conclusion": "scoped",
            "ref": "implementation.md",
        },
        review={"status": "done", "ref": "review.md"},
        working_scope=["   "],
        risk_triggers=["   "],
        confirmations=[
            {
                "type": "risk_acceptance",
                "source": "user",
                "note": "用户确认该高风险边界。",
            }
        ],
    )

    check = evaluate_task_transition(blank_ready_high_task, TaskStage.IN_PROGRESS)

    assert check.allowed is False
    assert "missing_high_risk_working_scope" in check.reason_codes
    assert "missing_high_risk_triggers" in check.reason_codes

    missing_implementation = evaluate_task_transition(
        task(),
        TaskStage.IN_PROGRESS,
    )
    assert missing_implementation.allowed is False
    assert "missing_implementation_ready" in missing_implementation.reason_codes

    no_service_refs = evaluate_task_transition(
        task(implementation={"ready": True, "conclusion": "scoped"}, service_refs=[]),
        TaskStage.IN_PROGRESS,
    )

    assert no_service_refs.allowed is True
    assert no_service_refs.reason_codes == ()


def test_component_signal_alone_does_not_escalate_risk() -> None:
    local_sql_task = task(
        implementation={"ready": True, "conclusion": "scoped"},
        process_level="micro",
        risk_level="low",
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
        },
    )

    check = evaluate_task_transition(local_sql_task, TaskStage.IN_PROGRESS)

    assert check.allowed is True
    assert check.reason_codes == ()


def test_real_data_write_profile_blocks_low_micro_in_progress() -> None:
    data_write_task = task(
        implementation={"ready": True, "conclusion": "scoped"},
        process_level="micro",
        risk_level="low",
        impact_profile={
            "action": "data_write",
            "component_signals": ["sql", "database"],
            "environment": "shared",
            "data_effect": "real_data_write",
            "external_effect": "write",
            "blast_radius": "shared_users",
            "reversibility": "hard",
            "contract_change": False,
            "security_or_permission": False,
            "verification_confidence": "integration_required",
        },
    )

    check = evaluate_task_transition(data_write_task, TaskStage.IN_PROGRESS)

    assert check.allowed is False
    assert "impact_profile_requires_risk_escalation" in check.reason_codes
    assert "impact_profile_requires_process_escalation" in check.reason_codes


def test_unknown_impact_profile_blocks_micro_in_progress() -> None:
    unknown_task = task(
        implementation={"ready": True, "conclusion": "scoped"},
        process_level="micro",
        risk_level="low",
        impact_profile={
            "action": "code_change",
            "environment": "unknown",
            "data_effect": "none",
            "external_effect": "none",
            "blast_radius": "unknown",
            "reversibility": "unknown",
            "contract_change": "unknown",
            "security_or_permission": "unknown",
            "verification_confidence": "unclear",
        },
    )

    check = evaluate_task_transition(unknown_task, TaskStage.IN_PROGRESS)

    assert check.allowed is False
    assert "impact_profile_unknown_for_micro" in check.reason_codes


def test_high_or_critical_in_progress_requires_extra_readiness() -> None:
    high_task = task(
        risk_level="high",
        implementation={"ready": True, "conclusion": "scoped"},
    )

    check = evaluate_task_transition(high_task, TaskStage.IN_PROGRESS)

    assert check.allowed is False
    assert "missing_high_risk_review" in check.reason_codes
    assert "missing_high_risk_implementation_ref" in check.reason_codes
    assert "missing_high_risk_working_scope" in check.reason_codes
    assert "missing_high_risk_triggers" in check.reason_codes
    assert "missing_high_risk_acceptance" in check.reason_codes

    ready_high_task = task(
        process_level="critical",
        implementation={
            "ready": True,
            "conclusion": "scoped",
            "ref": "implementation.md",
        },
        review={"status": "done", "ref": "review.md"},
        working_scope=["src/demo.py"],
        risk_triggers=["触发真实数据写入时暂停确认。"],
        confirmations=[
            {
                "type": "risk_acceptance",
                "source": "user",
                "note": "用户确认该高风险边界。",
            }
        ],
    )

    allowed = evaluate_task_transition(ready_high_task, TaskStage.IN_PROGRESS)

    assert allowed.allowed is True
    assert allowed.reason_codes == ()


def test_done_requires_passed_validation_evidence_and_resolved_handoff() -> None:
    done_ready = task(
        validation={"status": "passed", "evidence_ref": "EV-TASK-demo"},
        handoff={"status": "accepted", "note": "用户验收通过。"},
    )

    allowed = evaluate_task_transition(done_ready, TaskStage.DONE)

    assert allowed.allowed is True
    assert allowed.reason_codes == ()

    no_evidence = evaluate_task_transition(
        task(validation={"status": "passed"}, handoff={"status": "accepted", "note": "用户验收通过。"}),
        TaskStage.DONE,
    )
    assert no_evidence.allowed is False
    assert "missing_evidence" in no_evidence.reason_codes

    waiting_handoff = evaluate_task_transition(
        task(
            validation={"status": "passed", "evidence_ref": "EV-TASK-demo"},
            handoff={"status": "waiting_user_validation"},
        ),
        TaskStage.DONE,
    )
    assert waiting_handoff.allowed is False
    assert "handoff_waiting" in waiting_handoff.reason_codes


def test_obsolete_requires_dedicated_workflow() -> None:
    check = evaluate_task_transition(task(), TaskStage.OBSOLETE)

    assert check.allowed is False
    assert "missing_obsolete_reason" in check.reason_codes

    obsolete_ready = evaluate_task_transition(
        task(obsolete_reason="误建任务，已降级。"),
        TaskStage.OBSOLETE,
    )

    assert obsolete_ready.allowed is True


def test_micro_process_level_does_not_skip_done_guards() -> None:
    micro_task = task(
        process_level="micro",
        validation={"status": "passed"},
        handoff={"status": "not_required"},
    )

    check = evaluate_task_transition(micro_task, TaskStage.DONE)

    assert check.allowed is False
    assert "missing_evidence" in check.reason_codes


def test_blocked_stage_requires_resume_condition() -> None:
    blocked_task = task(
        blocked={
            "reason": "等待用户补充验收口径",
            "blocked_by": "user",
            "resume_condition": "用户补充完成口径",
            "resume_stage": "ready",
        }
    )

    check = evaluate_task_transition(blocked_task, TaskStage.BLOCKED)

    assert check.allowed is True

    incomplete_blocked = task(blocked={"reason": "等待用户"})
    blocked_check = evaluate_task_transition(incomplete_blocked, TaskStage.BLOCKED)

    assert blocked_check.allowed is False
    assert "missing_blocked_resume_condition" in blocked_check.reason_codes

    missing_blocked_by = task(
        blocked={
            "reason": "等待用户补充验收口径",
            "resume_condition": "用户补充完成口径",
            "resume_stage": "ready",
        }
    )
    blocked_by_check = evaluate_task_transition(missing_blocked_by, TaskStage.BLOCKED)

    assert blocked_by_check.allowed is False
    assert "missing_blocked_by" in blocked_by_check.reason_codes


def test_action_note_cannot_support_task_validation() -> None:
    current_task = task()
    evidence = EvidenceState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id="EV-TASK-demo",
        task_id=current_task.id,
        conclusion="passed",
        key_outputs=["python -m pytest passed"],
    )
    action = ActionNoteState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id="ACT-demo",
        title="Restart local helper",
        updated_at="2026-07-01",
        summary="记录一次本地辅助动作。",
        action_type="maintenance_action",
        related_refs=[current_task.id],
        side_effect_summary="no_side_effect",
        rollback_hint="no_rollback_needed",
    )

    evidence_check = evaluate_validation_record(current_task, evidence)
    action_check = evaluate_validation_record(current_task, action)

    assert evidence_check.allowed is True
    assert action_check.allowed is False
    assert "action_note_is_not_evidence" in action_check.reason_codes


def test_suspicion_log_cannot_support_task_validation() -> None:
    current_task = task()
    suspicion = SuspicionState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id="SUS-demo",
        title="记录疑点",
        updated_at="2026-07-01",
        location_or_subject="src/demo.py",
        confirmed_facts=["发现不一致现象。"],
        ai_inferences=["可能需要后续复核。"],
        current_task_impact="不影响当前任务。",
        suggested_handling="后续单独评估。",
        related_refs=[current_task.id],
    )

    check = evaluate_validation_record(current_task, suspicion)

    assert check.allowed is False
    assert "suspicion_log_is_not_evidence" in check.reason_codes


def test_handoff_waiting_cannot_archive() -> None:
    waiting_task = task(
        stage="done",
        validation={"status": "passed", "evidence_ref": "EV-TASK-demo"},
        handoff={"status": "waiting_user_validation"},
    )

    check = evaluate_archive_task(waiting_task)

    assert check.allowed is False
    assert "handoff_waiting" in check.reason_codes


def test_obsolete_archive_requires_reason() -> None:
    missing_reason = evaluate_archive_task(task(stage="obsolete"))
    with_reason = evaluate_archive_task(task(stage="obsolete", obsolete_reason="误建任务。"))

    assert missing_reason.allowed is False
    assert "missing_obsolete_reason" in missing_reason.reason_codes
    assert with_reason.allowed is True


def test_requirement_must_be_readable_before_formal_task() -> None:
    raw_requirement = RequirementState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id="REQ-20260702-001",
        title="Demo requirement",
        goal="Build a workbench",
        created_at="2026-07-01T08:00:00+08:00",
        updated_at="2026-07-01T08:00:00+08:00",
        acceptance=["Lifecycle guards exist"],
        readiness={"status": "raw_materials", "confirmed_by_user": False},
    )
    readable_requirement = RequirementState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id="REQ-20260702-002",
        title="Readable requirement",
        goal="Build a workbench",
        created_at="2026-07-01T08:30:00+08:00",
        updated_at="2026-07-01T08:30:00+08:00",
        acceptance=["Lifecycle guards exist"],
        readiness={"status": "readable", "confirmed_by_user": True},
    )

    raw_check = requirement_allows_formal_task(raw_requirement)
    readable_check = requirement_allows_formal_task(readable_requirement)
    micro_snapshot_check = requirement_allows_formal_task(
        raw_requirement,
        has_micro_requirement_snapshot=True,
    )

    assert raw_check.allowed is False
    assert "requirement_not_readable" in raw_check.reason_codes
    assert readable_check.allowed is True
    assert micro_snapshot_check.allowed is True


def test_fact_source_conflicts_keep_higher_maturity_source() -> None:
    assert (
        stronger_fact_source(FactSource.EVIDENCE, FactSource.TASK_YAML_NEXT_STEP)
        is FactSource.EVIDENCE
    )
    assert (
        stronger_fact_source(FactSource.LIVE_EVIDENCE, FactSource.AI_INFERENCE)
        is FactSource.LIVE_EVIDENCE
    )
