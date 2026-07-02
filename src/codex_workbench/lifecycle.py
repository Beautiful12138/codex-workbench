from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import (
    ActionNoteState,
    BlastRadius,
    ConfirmationType,
    DataEffect,
    EvidenceState,
    ExternalEffect,
    HandoffStatus,
    ImpactEnvironment,
    ProcessLevel,
    ReadinessConclusion,
    RequirementReadinessStatus,
    Reversibility,
    RequirementState,
    ReviewStatus,
    RiskLevel,
    SuspicionState,
    TaskStage,
    TaskState,
    ValidationStatus,
    VerificationConfidence,
)


@dataclass(frozen=True)
class LifecycleCheck:
    allowed: bool
    reason_codes: tuple[str, ...] = ()


class FactSource(str, Enum):
    LIVE_EVIDENCE = "live_evidence"
    EVIDENCE = "evidence"
    ACTION_NOTE = "action_note"
    PROGRESS = "progress"
    REQUIREMENT = "requirement"
    DISCOVERY = "discovery"
    GENERATED_INDEX = "generated_index"
    TASK_YAML_NEXT_STEP = "task_yaml_next_step"
    AI_INFERENCE = "ai_inference"
    ASSUMPTION = "assumption"


FACT_SOURCE_PRIORITY: dict[FactSource, int] = {
    FactSource.LIVE_EVIDENCE: 100,
    FactSource.EVIDENCE: 90,
    FactSource.ACTION_NOTE: 80,
    FactSource.PROGRESS: 70,
    FactSource.REQUIREMENT: 60,
    FactSource.DISCOVERY: 50,
    FactSource.GENERATED_INDEX: 40,
    FactSource.TASK_YAML_NEXT_STEP: 30,
    FactSource.AI_INFERENCE: 20,
    FactSource.ASSUMPTION: 10,
}


def _allowed() -> LifecycleCheck:
    return LifecycleCheck(allowed=True)


def _blocked(reason_codes: list[str]) -> LifecycleCheck:
    return LifecycleCheck(allowed=False, reason_codes=tuple(dict.fromkeys(reason_codes)))


def evaluate_task_transition(
    task: TaskState,
    target_stage: TaskStage,
) -> LifecycleCheck:
    target = TaskStage(target_stage)
    reason_codes: list[str] = []

    if target is TaskStage.IN_PROGRESS:
        if not task.implementation.ready or task.implementation.conclusion is not ReadinessConclusion.SCOPED:
            reason_codes.append("missing_implementation_ready")
        reason_codes.extend(_impact_profile_reason_codes(task))
        if _needs_high_pressure(task):
            if task.review.status is not ReviewStatus.DONE:
                reason_codes.append("missing_high_risk_review")
            if not task.implementation.ref:
                reason_codes.append("missing_high_risk_implementation_ref")
            if not _has_nonempty_items(task.working_scope):
                reason_codes.append("missing_high_risk_working_scope")
            if not _has_nonempty_items(task.risk_triggers):
                reason_codes.append("missing_high_risk_triggers")
            if not any(
                confirmation.type is ConfirmationType.RISK_ACCEPTANCE
                and (confirmation.note or "").strip()
                for confirmation in task.confirmations
            ):
                reason_codes.append("missing_high_risk_acceptance")

    if target is TaskStage.BLOCKED:
        if task.blocked is None:
            reason_codes.append("missing_blocked_state")
        else:
            if not task.blocked.reason:
                reason_codes.append("missing_blocked_reason")
            if task.blocked.blocked_by is None:
                reason_codes.append("missing_blocked_by")
            if not task.blocked.resume_condition:
                reason_codes.append("missing_blocked_resume_condition")
            if task.blocked.resume_stage is None:
                reason_codes.append("missing_blocked_resume_stage")

    if target is TaskStage.DONE:
        reason_codes.extend(_done_reason_codes(task))

    if target is TaskStage.OBSOLETE:
        if not (task.obsolete_reason or "").strip():
            reason_codes.append("missing_obsolete_reason")

    return _blocked(reason_codes) if reason_codes else _allowed()


def _needs_high_pressure(task: TaskState) -> bool:
    return (
        task.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        or task.process_level in {ProcessLevel.HIGH, ProcessLevel.CRITICAL}
    )


def _impact_profile_reason_codes(task: TaskState) -> list[str]:
    profile = task.impact_profile
    if profile is None:
        return []

    reason_codes: list[str] = []
    if _impact_has_real_consequence(task):
        if task.risk_level is RiskLevel.LOW:
            reason_codes.append("impact_profile_requires_risk_escalation")
        if task.process_level is ProcessLevel.MICRO:
            reason_codes.append("impact_profile_requires_process_escalation")

    if task.process_level is ProcessLevel.MICRO and _impact_has_unknowns(task):
        reason_codes.append("impact_profile_unknown_for_micro")

    return reason_codes


def _impact_has_real_consequence(task: TaskState) -> bool:
    profile = task.impact_profile
    if profile is None:
        return False
    return (
        profile.environment in {ImpactEnvironment.SHARED, ImpactEnvironment.PRODUCTION}
        or profile.data_effect
        in {
            DataEffect.REAL_DATA_WRITE,
            DataEffect.SCHEMA_OR_MIGRATION,
            DataEffect.DESTRUCTIVE,
        }
        or profile.external_effect
        in {
            ExternalEffect.WRITE,
            ExternalEffect.DEPLOY,
            ExternalEffect.NOTIFY,
            ExternalEffect.COST,
            ExternalEffect.SECURITY,
        }
        or profile.blast_radius in {BlastRadius.SHARED_USERS, BlastRadius.EXTERNAL_USERS}
        or profile.reversibility in {Reversibility.HARD, Reversibility.IRREVERSIBLE}
        or profile.contract_change is True
        or profile.security_or_permission is True
    )


def _impact_has_unknowns(task: TaskState) -> bool:
    profile = task.impact_profile
    if profile is None:
        return False
    return (
        profile.environment is ImpactEnvironment.UNKNOWN
        or profile.blast_radius is BlastRadius.UNKNOWN
        or profile.reversibility is Reversibility.UNKNOWN
        or profile.contract_change == "unknown"
        or profile.security_or_permission == "unknown"
        or profile.verification_confidence is VerificationConfidence.UNCLEAR
    )


def _has_nonempty_items(values: list[str]) -> bool:
    return any(value.strip() for value in values)


def requirement_allows_formal_task(
    requirement: RequirementState,
    *,
    has_micro_requirement_snapshot: bool = False,
) -> LifecycleCheck:
    if has_micro_requirement_snapshot:
        return _allowed()
    if (
        requirement.readiness.status is RequirementReadinessStatus.READABLE
        and requirement.readiness.confirmed_by_user
    ):
        return _allowed()
    reason_codes = ["requirement_not_readable"]
    if not requirement.readiness.confirmed_by_user:
        reason_codes.append("missing_user_confirmation")
    return _blocked(reason_codes)


def stronger_fact_source(left: FactSource, right: FactSource) -> FactSource:
    left_source = FactSource(left)
    right_source = FactSource(right)
    if FACT_SOURCE_PRIORITY[left_source] >= FACT_SOURCE_PRIORITY[right_source]:
        return left_source
    return right_source


def evaluate_validation_record(
    task: TaskState,
    record: EvidenceState | ActionNoteState | SuspicionState,
) -> LifecycleCheck:
    if isinstance(record, ActionNoteState):
        return _blocked(["action_note_is_not_evidence"])
    if isinstance(record, SuspicionState):
        return _blocked(["suspicion_log_is_not_evidence"])
    if record.task_id != task.id:
        return _blocked(["evidence_task_mismatch"])
    return _allowed()


def evaluate_archive_task(task: TaskState) -> LifecycleCheck:
    reason_codes: list[str] = []
    if task.stage not in {TaskStage.DONE, TaskStage.OBSOLETE}:
        reason_codes.append("task_not_closed")
    if task.handoff.status is HandoffStatus.WAITING_USER_VALIDATION:
        reason_codes.append("handoff_waiting")
    if task.stage is TaskStage.DONE:
        reason_codes.extend(_done_reason_codes(task))
    if task.stage is TaskStage.OBSOLETE and not (task.obsolete_reason or "").strip():
        reason_codes.append("missing_obsolete_reason")
    return _blocked(reason_codes) if reason_codes else _allowed()


def _done_reason_codes(task: TaskState) -> list[str]:
    reason_codes: list[str] = []
    if task.validation.status is not ValidationStatus.PASSED:
        reason_codes.append("validation_not_passed")
    if not task.validation.evidence_ref:
        reason_codes.append("missing_evidence")
    if task.validation.unverified_items:
        reason_codes.append("unverified_items_present")
    if task.handoff.status is HandoffStatus.WAITING_USER_VALIDATION:
        reason_codes.append("handoff_waiting")
    if task.handoff.status is HandoffStatus.ACCEPTED and not (task.handoff.note or "").strip():
        reason_codes.append("missing_handoff_note")
    if task.handoff.status is HandoffStatus.REJECTED:
        reason_codes.append("handoff_rejected")
    return reason_codes
