from __future__ import annotations

from pathlib import Path

from . import _package_core as package_core
from ._package_core import PackageWriteResult, TaskStageCheckResult
from .errors import ErrorCode, WorkbenchError
from .lifecycle import evaluate_task_transition
from .models import BlockedBy, ConfirmationType, TaskStage, TaskState
from .templates import (
    TaskDocumentTemplateContext,
    render_implementation_document,
    render_review_document,
)
from .timeutils import resolve_timestamp


def update_task_packet(
    workspace_root: str | Path,
    task_id: str,
    *,
    next_step: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    clean_next_step = package_core._clean_required(next_step, "missing_next_step")
    data["next_step"] = clean_next_step
    data["updated_at"] = resolve_timestamp(updated_at)
    TaskState.model_validate(data)
    package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def set_task_stage(
    workspace_root: str | Path,
    task_id: str,
    stage: str,
    *,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    task_yaml = package_core._package_file(root, "docs/active", task_id, "task.yaml")
    snapshot = package_core.read_yaml_with_version(task_yaml)
    data = snapshot.data
    task = TaskState.model_validate(data)
    if task.id != task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={task_id} actual={task.id}",
            exit_code=2,
        )
    try:
        target_stage = TaskStage(stage)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_stage: {stage}",
            exit_code=2,
        ) from exc

    check = evaluate_task_transition(task, target_stage)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"stage_transition_blocked: {reasons}",
            exit_code=2,
        )
    if target_stage is TaskStage.IN_PROGRESS:
        package_core._assert_known_service_refs(root, task)
    if target_stage is TaskStage.DONE:
        from .validation import assert_done_evidence_valid

        assert_done_evidence_valid(root, task)

    data["stage"] = target_stage.value
    data["updated_at"] = resolve_timestamp(updated_at)
    package_core.write_yaml_atomic(
        task_yaml, data, dry_run=dry_run, expected_version=snapshot.version
    )
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def check_task_stage(
    workspace_root: str | Path,
    task_id: str,
    stage: str,
) -> TaskStageCheckResult:
    root, _, _, task, _ = package_core._load_task_package(workspace_root, task_id)
    try:
        target_stage = TaskStage(stage)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_stage: {stage}",
            exit_code=2,
        ) from exc

    check = evaluate_task_transition(task, target_stage)
    reason_codes = list(check.reason_codes)

    if target_stage is TaskStage.IN_PROGRESS:
        try:
            package_core._assert_known_service_refs(root, task)
        except WorkbenchError as exc:
            reason_codes.append(exc.message)
    if target_stage is TaskStage.DONE:
        from .validation import assert_done_evidence_valid

        try:
            assert_done_evidence_valid(root, task)
        except WorkbenchError as exc:
            reason_codes.append(exc.message)

    return package_core.TaskStageCheckResult(
        task_id=task.id,
        target_stage=target_stage,
        allowed=not reason_codes,
        reason_codes=tuple(reason_codes),
    )


def prepare_task(
    workspace_root: str | Path,
    task_id: str,
    *,
    working_scope: list[str],
    process_level: str | None = None,
    risk_level: str | None = None,
    impact_profile: dict | None = None,
    impact_reason: str | None = None,
    implementation_ref: str | None = None,
    review_ref: str | None = None,
    reviewer: str | None = None,
    review_independent: bool = False,
    risk_acceptance_note: str | None = None,
    likely_touchpoints: list[str] | None = None,
    risk_triggers: list[str] | None = None,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    scope = package_core._clean_required_list(working_scope, "missing_working_scope")

    implementation = data.setdefault("implementation", {})
    if not isinstance(implementation, dict):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "invalid_implementation_state",
            exit_code=2,
        )
    implementation["ready"] = True
    implementation["conclusion"] = "scoped"
    if implementation_ref and implementation_ref.strip():
        implementation["ref"] = implementation_ref.strip()

    data["working_scope"] = scope
    touchpoints = package_core._clean_list(likely_touchpoints or [])
    if touchpoints:
        data["likely_touchpoints"] = touchpoints
    triggers = package_core._clean_list(risk_triggers or [])
    if triggers:
        data["risk_triggers"] = triggers

    package_core._apply_task_impact_update(
        data,
        process_level=process_level,
        risk_level=risk_level,
        impact_profile=impact_profile,
        risk_triggers=None,
        reason=impact_reason,
        require_reason=False,
    )

    if (review_ref and review_ref.strip()) or (reviewer and reviewer.strip()) or review_independent:
        review = data.setdefault("review", {})
        if not isinstance(review, dict):
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                "invalid_review_state",
                exit_code=2,
            )
        if review_ref and review_ref.strip():
            review["status"] = "done"
            review["ref"] = review_ref.strip()
        if reviewer and reviewer.strip():
            review["reviewer"] = reviewer.strip()
        if review_independent:
            review["independent"] = True

    if risk_acceptance_note and risk_acceptance_note.strip():
        confirmations = data.setdefault("confirmations", [])
        if not isinstance(confirmations, list):
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                "invalid_confirmations_state",
                exit_code=2,
            )
        confirmations.append(
            {
                "type": ConfirmationType.RISK_ACCEPTANCE.value,
                "source": "user",
                "note": risk_acceptance_note.strip(),
            }
        )

    data["updated_at"] = resolve_timestamp(updated_at)
    task = TaskState.model_validate(data)
    if task.id != task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={task_id} actual={task.id}",
            exit_code=2,
        )
    package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def update_task_impact(
    workspace_root: str | Path,
    task_id: str,
    *,
    process_level: str | None = None,
    risk_level: str | None = None,
    impact_profile: dict | None = None,
    risk_triggers: list[str] | None = None,
    reason: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    package_core._apply_task_impact_update(
        data,
        process_level=process_level,
        risk_level=risk_level,
        impact_profile=impact_profile,
        risk_triggers=risk_triggers,
        reason=reason,
        require_reason=True,
    )
    data["updated_at"] = resolve_timestamp(updated_at)
    task = TaskState.model_validate(data)
    if task.id != task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={task_id} actual={task.id}",
            exit_code=2,
        )
    package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def create_task_review_document(
    workspace_root: str | Path,
    task_id: str,
    *,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    context = TaskDocumentTemplateContext(task_id=task.id)
    files = render_review_document(context)
    review = data.setdefault("review", {})
    if not isinstance(review, dict):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "invalid_review_state",
            exit_code=2,
        )
    review["ref"] = "review.md"
    if review.get("status") in (None, "not_started"):
        review["status"] = "pending"
    data["updated_at"] = resolve_timestamp(updated_at)
    TaskState.model_validate(data)
    result = package_core.write_package_files(root, files, dry_run=dry_run)
    try:
        package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    except WorkbenchError:
        package_core._rollback_created_files(
            result.paths,
            dry_run=dry_run,
            expected_contents=package_core._expected_file_contents(root, files),
        )
        raise
    return package_core.PackageWriteResult(paths=(*result.paths, task_yaml), dry_run=dry_run)


def create_task_implementation_document(
    workspace_root: str | Path,
    task_id: str,
    *,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    context = TaskDocumentTemplateContext(task_id=task.id)
    files = render_implementation_document(context)
    implementation = data.setdefault("implementation", {})
    if not isinstance(implementation, dict):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "invalid_implementation_state",
            exit_code=2,
        )
    implementation["ref"] = "implementation.md"
    data["updated_at"] = resolve_timestamp(updated_at)
    TaskState.model_validate(data)
    result = package_core.write_package_files(root, files, dry_run=dry_run)
    try:
        package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    except WorkbenchError:
        package_core._rollback_created_files(
            result.paths,
            dry_run=dry_run,
            expected_contents=package_core._expected_file_contents(root, files),
        )
        raise
    return package_core.PackageWriteResult(paths=(*result.paths, task_yaml), dry_run=dry_run)


def block_task(
    workspace_root: str | Path,
    task_id: str,
    *,
    reason: str,
    blocked_by: str,
    resume_condition: str,
    resume_stage: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    try:
        blocked_by_value = BlockedBy(blocked_by)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_blocked_by: {blocked_by}",
            exit_code=2,
        ) from exc
    try:
        resume_stage_value = TaskStage(resume_stage)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_stage: {resume_stage}",
            exit_code=2,
        ) from exc
    if resume_stage_value in {TaskStage.BLOCKED, TaskStage.DONE, TaskStage.OBSOLETE}:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_blocked_resume_stage: {resume_stage_value.value}",
            exit_code=2,
        )

    data["blocked"] = {
        "reason": package_core._clean_required(reason, "missing_blocked_reason"),
        "blocked_by": blocked_by_value.value,
        "resume_condition": package_core._clean_required(
            resume_condition, "missing_blocked_resume_condition"
        ),
        "resume_stage": resume_stage_value.value,
    }
    task = TaskState.model_validate(data)
    check = evaluate_task_transition(task, TaskStage.BLOCKED)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"stage_transition_blocked: {reasons}",
            exit_code=2,
        )
    data["stage"] = TaskStage.BLOCKED.value
    data["updated_at"] = resolve_timestamp(updated_at)
    package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def obsolete_task(
    workspace_root: str | Path,
    task_id: str,
    *,
    reason: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task, version = package_core._load_task_package(workspace_root, task_id)
    data["obsolete_reason"] = package_core._clean_required(reason, "missing_obsolete_reason")
    task = TaskState.model_validate(data)
    check = evaluate_task_transition(task, TaskStage.OBSOLETE)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"stage_transition_blocked: {reasons}",
            exit_code=2,
        )
    data["stage"] = TaskStage.OBSOLETE.value
    data["updated_at"] = resolve_timestamp(updated_at)
    package_core.write_yaml_atomic(task_yaml, data, dry_run=dry_run, expected_version=version)
    return package_core.PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)
