from __future__ import annotations

from .models import (
    BlastRadius,
    DataEffect,
    ExternalEffect,
    ImpactEnvironment,
    ProcessLevel,
    Reversibility,
    RiskLevel,
    TaskState,
    VerificationConfidence,
)


def impact_gate_reason_codes(task: TaskState) -> list[str]:
    """Return lifecycle-blocking risk reasons derived from task impact profile."""
    profile = task.impact_profile
    reason_codes: list[str] = []
    if profile is None:
        if _needs_high_pressure(task):
            reason_codes.append("missing_high_risk_impact_profile")
        return reason_codes

    if impact_has_real_consequence(task):
        if task.risk_level is RiskLevel.LOW:
            reason_codes.append("impact_profile_requires_risk_escalation")
        if task.process_level is ProcessLevel.MICRO:
            reason_codes.append("impact_profile_requires_process_escalation")

    if task.process_level is ProcessLevel.MICRO and impact_has_unknowns(task):
        reason_codes.append("impact_profile_unknown_for_micro")

    return reason_codes


def risk_gap_reason_codes(task: TaskState) -> list[str]:
    """Return short recovery/index risk gaps; these are not all doctor findings."""
    if task.impact_profile is None:
        if task.risk_level is not RiskLevel.LOW or task.process_level not in {
            ProcessLevel.MICRO,
            ProcessLevel.LIGHTWEIGHT,
        }:
            return ["missing_impact_profile"]
        return []
    return impact_gate_reason_codes(task)


def risk_level_summary(task: TaskState) -> str:
    return f"{task.risk_level.value}/{task.process_level.value}"


def impact_summary(task: TaskState) -> str:
    profile = task.impact_profile
    if profile is None:
        return "missing"
    return (
        f"{profile.action.value} {profile.environment.value} "
        f"data={profile.data_effect.value} external={profile.external_effect.value} "
        f"radius={profile.blast_radius.value} rollback={profile.reversibility.value}"
    )


def risk_gap_summary(task: TaskState) -> str:
    gaps = risk_gap_reason_codes(task)
    return ",".join(gaps) if gaps else "none"


def impact_has_real_consequence(task: TaskState) -> bool:
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


def impact_has_unknowns(task: TaskState) -> bool:
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


def _needs_high_pressure(task: TaskState) -> bool:
    return (
        task.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        or task.process_level in {ProcessLevel.HIGH, ProcessLevel.CRITICAL}
    )
