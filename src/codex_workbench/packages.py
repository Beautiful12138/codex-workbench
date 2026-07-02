from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, write_text_utf8_atomic, write_yaml_atomic
from .lifecycle import evaluate_task_transition, requirement_allows_formal_task
from .models import BlockedBy, ConfirmationType, RequirementState, TaskStage, TaskState
from .refs import validate_package_ref
from .services import read_service_registry
from .templates import (
    RequirementTemplateContext,
    TaskDocumentTemplateContext,
    TaskTemplateContext,
    render_implementation_document,
    render_requirement_package,
    render_review_document,
    render_task_package,
)
from .workspace import resolve_workspace_path


INITIAL_CREATE_STAGES = {TaskStage.DRAFT}
FINAL_CREATE_STAGES = {TaskStage.DONE, TaskStage.OBSOLETE}
@dataclass(frozen=True)
class PackageWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool


@dataclass(frozen=True)
class TaskStageCheckResult:
    task_id: str
    target_stage: TaskStage
    allowed: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementTaskRefUpdate:
    path: Path
    data: dict


def create_requirement_package(
    workspace_root: str | Path,
    context: RequirementTemplateContext,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> PackageWriteResult:
    files = render_requirement_package(context)
    requirement_yaml = yaml.safe_load(next(content for path, content in files.items() if path.endswith("requirement.yaml")))
    RequirementState.model_validate(requirement_yaml)
    return write_package_files(workspace_root, files, dry_run=dry_run, overwrite=overwrite)


def create_task_package(
    workspace_root: str | Path,
    context: TaskTemplateContext,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> PackageWriteResult:
    _validate_new_package_id(context.task_id)
    validate_package_ref(context.requirement_id)
    try:
        stage = TaskStage(context.stage)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_stage: {context.stage}",
            exit_code=2,
        ) from exc
    if stage in FINAL_CREATE_STAGES:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"final_stage_not_allowed: {stage.value}",
            exit_code=2,
        )
    if stage not in INITIAL_CREATE_STAGES:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"initial_stage_not_allowed: {stage.value}",
            exit_code=2,
        )

    root = Path(workspace_root).expanduser().resolve()
    _assert_task_id_matches_requirement(context.requirement_id, context.task_id)
    requirement_update = _prepare_requirement_task_ref_update(
        root,
        context.requirement_id,
        context.task_id,
    )
    files = render_task_package(context)
    task_yaml = yaml.safe_load(next(content for path, content in files.items() if path.endswith("task.yaml")))
    TaskState.model_validate(task_yaml)
    result = write_package_files(workspace_root, files, dry_run=dry_run, overwrite=overwrite)
    try:
        write_yaml_atomic(requirement_update.path, requirement_update.data, dry_run=dry_run)
    except WorkbenchError:
        _rollback_created_files(result.paths, dry_run=dry_run)
        raise
    return PackageWriteResult(
        paths=(*result.paths, requirement_update.path),
        dry_run=dry_run,
    )


def close_requirement(
    workspace_root: str | Path,
    requirement_id: str,
    *,
    note: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    clean_requirement_id = validate_package_ref(requirement_id)
    clean_note = note.strip()
    if not clean_note:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_requirement_closure_note",
            exit_code=2,
        )

    root = Path(workspace_root).expanduser().resolve()
    path = _package_file(root, "docs/active", clean_requirement_id, "requirement.yaml")
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {clean_requirement_id}",
            exit_code=2,
        )

    data = read_yaml(path)
    requirement = RequirementState.model_validate(data)
    if requirement.id != clean_requirement_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_id_mismatch: expected={clean_requirement_id} actual={requirement.id}",
            exit_code=2,
        )
    check = requirement_allows_formal_task(requirement)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_not_readable: {reasons}",
            exit_code=2,
        )

    confirmations = data.setdefault("confirmations", [])
    has_closure = any(
        isinstance(item, dict)
        and item.get("type") == ConfirmationType.REQUIREMENT_CLOSURE.value
        for item in confirmations
    )
    if not has_closure:
        confirmations.append(
            {
                "type": ConfirmationType.REQUIREMENT_CLOSURE.value,
                "source": "user",
                "note": clean_note,
            }
        )
    if updated_at:
        data["updated_at"] = updated_at
    RequirementState.model_validate(data)
    write_yaml_atomic(path, data, dry_run=dry_run)
    return PackageWriteResult(paths=(path,), dry_run=dry_run)


def update_task_packet(
    workspace_root: str | Path,
    task_id: str,
    *,
    next_step: str,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
    clean_next_step = _clean_required(next_step, "missing_next_step")
    data["next_step"] = clean_next_step
    TaskState.model_validate(data)
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def set_task_stage(
    workspace_root: str | Path,
    task_id: str,
    stage: str,
    *,
    dry_run: bool = False,
) -> PackageWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    task_yaml = _package_file(root, "docs/active", task_id, "task.yaml")
    data = read_yaml(task_yaml)
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
        _assert_known_service_refs(root, task)
    if target_stage is TaskStage.DONE:
        from .validation import assert_done_evidence_valid

        assert_done_evidence_valid(root, task)

    data["stage"] = target_stage.value
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def check_task_stage(
    workspace_root: str | Path,
    task_id: str,
    stage: str,
) -> TaskStageCheckResult:
    root, _, _, task = _load_task_package(workspace_root, task_id)
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
            _assert_known_service_refs(root, task)
        except WorkbenchError as exc:
            reason_codes.append(exc.message)
    if target_stage is TaskStage.DONE:
        from .validation import assert_done_evidence_valid

        try:
            assert_done_evidence_valid(root, task)
        except WorkbenchError as exc:
            reason_codes.append(exc.message)

    return TaskStageCheckResult(
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
    implementation_ref: str | None = None,
    review_ref: str | None = None,
    risk_acceptance_note: str | None = None,
    likely_touchpoints: list[str] | None = None,
    risk_triggers: list[str] | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
    scope = _clean_required_list(working_scope, "missing_working_scope")

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
    touchpoints = _clean_list(likely_touchpoints or [])
    if touchpoints:
        data["likely_touchpoints"] = touchpoints
    triggers = _clean_list(risk_triggers or [])
    if triggers:
        data["risk_triggers"] = triggers

    if review_ref and review_ref.strip():
        data["review"] = {"status": "done", "ref": review_ref.strip()}

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

    task = TaskState.model_validate(data)
    if task.id != task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={task_id} actual={task.id}",
            exit_code=2,
        )
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def create_task_review_document(
    workspace_root: str | Path,
    task_id: str,
    *,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
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
    TaskState.model_validate(data)
    result = write_package_files(root, files, dry_run=dry_run)
    try:
        write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    except WorkbenchError:
        _rollback_created_files(result.paths, dry_run=dry_run)
        raise
    return PackageWriteResult(paths=(*result.paths, task_yaml), dry_run=dry_run)


def create_task_implementation_document(
    workspace_root: str | Path,
    task_id: str,
    *,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
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
    TaskState.model_validate(data)
    result = write_package_files(root, files, dry_run=dry_run)
    try:
        write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    except WorkbenchError:
        _rollback_created_files(result.paths, dry_run=dry_run)
        raise
    return PackageWriteResult(paths=(*result.paths, task_yaml), dry_run=dry_run)


def block_task(
    workspace_root: str | Path,
    task_id: str,
    *,
    reason: str,
    blocked_by: str,
    resume_condition: str,
    resume_stage: str,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
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
        "reason": _clean_required(reason, "missing_blocked_reason"),
        "blocked_by": blocked_by_value.value,
        "resume_condition": _clean_required(resume_condition, "missing_blocked_resume_condition"),
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
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def obsolete_task(
    workspace_root: str | Path,
    task_id: str,
    *,
    reason: str,
    dry_run: bool = False,
) -> PackageWriteResult:
    root, task_yaml, data, task = _load_task_package(workspace_root, task_id)
    data["obsolete_reason"] = _clean_required(reason, "missing_obsolete_reason")
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
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return PackageWriteResult(paths=(task_yaml,), dry_run=dry_run)


def write_package_files(
    workspace_root: str | Path,
    files: dict[str, str],
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> PackageWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    targets: list[tuple[Path, str]] = []

    for relative_path, content in files.items():
        if _has_path_traversal(relative_path):
            raise WorkbenchError(
                ErrorCode.PATH_OUTSIDE_WORKSPACE,
                f"path_outside_workspace: {relative_path}",
                exit_code=2,
            )
        target = resolve_workspace_path(root, relative_path)
        targets.append((target, content))

    if not overwrite:
        existing = [path for path, _ in targets if path.exists()]
        if existing:
            first = existing[0].relative_to(root).as_posix()
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"already_exists: {first}",
                exit_code=2,
            )

    for path, content in targets:
        write_text_utf8_atomic(path, content, dry_run=dry_run)

    return PackageWriteResult(paths=tuple(path for path, _ in targets), dry_run=dry_run)


def _has_path_traversal(relative_path: str) -> bool:
    return any(part == ".." for part in Path(relative_path).parts)


def _validate_new_package_id(package_id: str) -> None:
    if any(part == ".." for part in Path(package_id).parts):
        raise WorkbenchError(
            ErrorCode.PATH_OUTSIDE_WORKSPACE,
            f"path_outside_workspace: {package_id}",
            exit_code=2,
        )
    validate_package_ref(package_id)


def _package_file(root: Path, base: str, package_id: str, filename: str) -> Path:
    relative_path = f"{base}/{package_id}/{filename}"
    if _has_path_traversal(relative_path):
        raise WorkbenchError(
            ErrorCode.PATH_OUTSIDE_WORKSPACE,
            f"path_outside_workspace: {relative_path}",
            exit_code=2,
        )
    return resolve_workspace_path(root, relative_path)


def _load_task_package(
    workspace_root: str | Path,
    task_id: str,
) -> tuple[Path, Path, dict, TaskState]:
    clean_task_id = validate_package_ref(task_id)
    root = Path(workspace_root).expanduser().resolve()
    task_yaml = _package_file(root, "docs/active", clean_task_id, "task.yaml")
    data = read_yaml(task_yaml)
    task = TaskState.model_validate(data)
    if task.id != clean_task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={clean_task_id} actual={task.id}",
            exit_code=2,
        )
    return root, task_yaml, data, task


def _clean_required(value: str, reason_code: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, reason_code, exit_code=2)
    return cleaned


def _clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _clean_required_list(values: list[str], reason_code: str) -> list[str]:
    cleaned = _clean_list(values)
    if not cleaned:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, reason_code, exit_code=2)
    return cleaned


def _assert_known_service_refs(root: Path, task: TaskState) -> None:
    if not task.service_refs:
        return
    registry = read_service_registry(root)
    known = {service.name for service in registry.services}
    unknown = [service_ref for service_ref in task.service_refs if service_ref not in known]
    if unknown:
        refs = ",".join(unknown)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"unknown_service_ref: {refs}",
            exit_code=2,
        )


def _assert_task_id_matches_requirement(requirement_id: str, task_id: str) -> None:
    clean_requirement_id = validate_package_ref(requirement_id)
    clean_task_id = validate_package_ref(task_id)
    if not clean_task_id.startswith(f"{clean_requirement_id}-"):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_requirement_prefix_mismatch: {clean_requirement_id} -> {clean_task_id}",
            exit_code=2,
        )


def _assert_requirement_allows_task(root: Path, requirement_id: str) -> None:
    requirement_yaml = _package_file(root, "docs/active", requirement_id, "requirement.yaml")
    if not requirement_yaml.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {requirement_id}",
            exit_code=2,
        )
    requirement = RequirementState.model_validate(read_yaml(requirement_yaml))
    check = requirement_allows_formal_task(requirement)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_not_readable: {reasons}",
            exit_code=2,
        )


def _prepare_requirement_task_ref_update(
    root: Path,
    requirement_id: str,
    task_id: str,
) -> RequirementTaskRefUpdate:
    clean_requirement_id = validate_package_ref(requirement_id)
    clean_task_id = validate_package_ref(task_id)
    requirement_yaml = _package_file(root, "docs/active", clean_requirement_id, "requirement.yaml")
    if not requirement_yaml.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {clean_requirement_id}",
            exit_code=2,
        )
    data = read_yaml(requirement_yaml)
    try:
        requirement = RequirementState.model_validate(data)
    except (ValidationError, WorkbenchError) as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_requirement_package: {clean_requirement_id}",
            exit_code=2,
        ) from exc
    if requirement.id != clean_requirement_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_id_mismatch: expected={clean_requirement_id} actual={requirement.id}",
            exit_code=2,
        )
    check = requirement_allows_formal_task(requirement)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_not_readable: {reasons}",
            exit_code=2,
        )
    task_refs = data.setdefault("task_refs", [])
    if not isinstance(task_refs, list):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_requirement_task_refs: {clean_requirement_id}",
            exit_code=2,
        )
    if clean_task_id not in task_refs:
        task_refs.append(clean_task_id)
    RequirementState.model_validate(data)
    return RequirementTaskRefUpdate(path=requirement_yaml, data=data)


def _rollback_created_files(paths: tuple[Path, ...], *, dry_run: bool) -> None:
    if dry_run:
        return
    parents = []
    for path in reversed(paths):
        if path.exists():
            path.unlink()
        parents.append(path.parent)
    for parent in sorted(set(parents), key=lambda item: len(item.parts), reverse=True):
        try:
            parent.rmdir()
        except OSError:
            pass
