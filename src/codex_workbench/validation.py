from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, write_text_utf8_atomic, write_yaml_atomic
from .lifecycle import evaluate_validation_record
from .models import (
    CURRENT_SCHEMA_VERSION,
    EvidenceState,
    HandoffStatus,
    TaskState,
    ValidationStatus,
)
from .refs import validate_package_ref
from .templates import EvidenceTemplateContext, TemplateError, render_evidence_document
from .timeutils import resolve_timestamp
from .workspace import resolve_workspace_path


EVIDENCE_CONCLUSIONS = {
    ValidationStatus.PASSED,
    ValidationStatus.FAILED,
    ValidationStatus.PARTIAL,
    ValidationStatus.CLOSED_WITH_EXCEPTION,
}
HANDOFF_NOTE_REQUIRED = {HandoffStatus.ACCEPTED, HandoffStatus.REJECTED}


@dataclass(frozen=True)
class ValidationWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool


def create_evidence_record(
    workspace_root: str | Path,
    *,
    evidence_id: str,
    task_id: str,
    conclusion: str,
    key_outputs: list[str],
    updated_at: str,
    unverified_items: list[str] | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> ValidationWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    evidence_id = validate_package_ref(evidence_id)
    task_id = validate_package_ref(task_id)
    key_outputs = _clean_list(key_outputs)
    unverified_items = _clean_list(unverified_items)
    if not key_outputs:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, "missing_key_outputs", exit_code=2)

    task = _read_task(root, task_id)
    try:
        conclusion_status = ValidationStatus(conclusion)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_validation_status: {conclusion}",
            exit_code=2,
        ) from exc
    _assert_evidence_conclusion(conclusion_status)

    evidence = EvidenceState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id=evidence_id,
        task_id=task.id,
        conclusion=conclusion_status,
        key_outputs=key_outputs,
        unverified_items=unverified_items,
    )
    context = EvidenceTemplateContext(
        evidence_id=evidence.id,
        task_id=evidence.task_id,
        conclusion=evidence.conclusion.value,
        key_outputs=evidence.key_outputs,
        unverified_items=evidence.unverified_items,
        updated_at=updated_at,
    )
    try:
        files = render_evidence_document(context)
    except TemplateError as exc:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, str(exc), exit_code=2) from exc

    evidence_yaml = _evidence_yaml_path(root, task_id)
    evidence_md = _evidence_md_path(root, task_id)
    targets = (
        (evidence_yaml, files[f"docs/active/{task_id}/evidence.yaml"]),
        (evidence_md, files[f"docs/active/{task_id}/evidence.md"]),
    )
    if not overwrite:
        for path, _ in targets:
            if path.exists():
                raise WorkbenchError(
                    ErrorCode.VALIDATION_ERROR,
                    f"already_exists: {path.relative_to(root).as_posix()}",
                    exit_code=2,
                )
    for path, content in targets:
        write_text_utf8_atomic(path, content, dry_run=dry_run)
    return ValidationWriteResult(paths=tuple(path for path, _ in targets), dry_run=dry_run)


def apply_validation(
    workspace_root: str | Path,
    *,
    task_id: str,
    evidence_id: str,
    status: str,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> ValidationWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    task_id = validate_package_ref(task_id)
    evidence_id = validate_package_ref(evidence_id)
    try:
        validation_status = ValidationStatus(status)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_validation_status: {status}",
            exit_code=2,
        ) from exc

    task_yaml = _task_yaml_path(root, task_id)
    data = read_yaml(task_yaml)
    task = _validate_task_data(data, task_id)
    evidence = _read_evidence_for_task(root, task, evidence_id)
    _assert_evidence_conclusion(evidence.conclusion)
    if evidence.conclusion is not validation_status:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"validation_status_mismatch: evidence={evidence.conclusion.value} requested={validation_status.value}",
            exit_code=2,
        )
    if validation_status is ValidationStatus.PASSED and evidence.unverified_items:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "evidence_has_unverified_items",
            exit_code=2,
        )

    data["validation"] = {
        "status": validation_status.value,
        "evidence_ref": evidence.id,
        "unverified_items": evidence.unverified_items,
    }
    data["updated_at"] = resolve_timestamp(updated_at)
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return ValidationWriteResult(paths=(task_yaml,), dry_run=dry_run)


def set_handoff_status(
    workspace_root: str | Path,
    *,
    task_id: str,
    status: str,
    note: str | None = None,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> ValidationWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    task_id = validate_package_ref(task_id)
    try:
        handoff_status = HandoffStatus(status)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_handoff_status: {status}",
            exit_code=2,
        ) from exc

    task_yaml = _task_yaml_path(root, task_id)
    data = read_yaml(task_yaml)
    _validate_task_data(data, task_id)
    note = note.strip() if note else None
    if handoff_status in HANDOFF_NOTE_REQUIRED and not note:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_handoff_note: {handoff_status.value}",
            exit_code=2,
        )
    payload: dict[str, Any] = {"status": handoff_status.value}
    if note:
        payload["note"] = note
    data["handoff"] = payload
    data["updated_at"] = resolve_timestamp(updated_at)
    write_yaml_atomic(task_yaml, data, dry_run=dry_run)
    return ValidationWriteResult(paths=(task_yaml,), dry_run=dry_run)


def assert_done_evidence_valid(workspace_root: str | Path, task: TaskState) -> None:
    root = Path(workspace_root).expanduser().resolve()
    evidence_ref = task.validation.evidence_ref
    if not evidence_ref:
        return
    evidence = _read_evidence_for_task(root, task, evidence_ref)
    _assert_evidence_conclusion(evidence.conclusion)
    if evidence.conclusion is not ValidationStatus.PASSED:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"evidence_not_passed: {evidence.conclusion.value}",
            exit_code=2,
        )
    if evidence.unverified_items:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "evidence_has_unverified_items",
            exit_code=2,
        )


def _read_task(root: Path, task_id: str) -> TaskState:
    data = read_yaml(_task_yaml_path(root, task_id))
    return _validate_task_data(data, task_id)


def _validate_task_data(data: Any, task_id: str) -> TaskState:
    try:
        task = TaskState.model_validate(data)
    except (ValidationError, WorkbenchError) as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_package: {task_id}",
            exit_code=2,
        ) from exc
    if task.id != task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={task_id} actual={task.id}",
            exit_code=2,
        )
    return task


def _read_evidence_for_task(root: Path, task: TaskState, evidence_id: str) -> EvidenceState:
    evidence_id = validate_package_ref(evidence_id)
    path = _evidence_yaml_path(root, task.id)
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_evidence_record: {evidence_id}",
            exit_code=2,
        )
    try:
        evidence = EvidenceState.model_validate(read_yaml(path))
    except (ValidationError, WorkbenchError) as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_evidence_record: {evidence_id}",
            exit_code=2,
        ) from exc
    validate_package_ref(evidence.id)
    if evidence.id != evidence_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"evidence_ref_mismatch: expected={evidence_id} actual={evidence.id}",
            exit_code=2,
        )
    check = evaluate_validation_record(task, evidence)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"validation_record_rejected: {reasons}",
            exit_code=2,
        )
    return evidence


def _assert_evidence_conclusion(status: ValidationStatus) -> None:
    if status not in EVIDENCE_CONCLUSIONS:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_evidence_conclusion: {status.value}",
            exit_code=2,
        )


def _task_yaml_path(root: Path, task_id: str) -> Path:
    task_id = validate_package_ref(task_id)
    return resolve_workspace_path(root, f"docs/active/{task_id}/task.yaml")


def _evidence_yaml_path(root: Path, task_id: str) -> Path:
    task_id = validate_package_ref(task_id)
    return resolve_workspace_path(root, f"docs/active/{task_id}/evidence.yaml")


def _evidence_md_path(root: Path, task_id: str) -> Path:
    task_id = validate_package_ref(task_id)
    return resolve_workspace_path(root, f"docs/active/{task_id}/evidence.md")


def _clean_list(items: list[str] | None) -> list[str]:
    return [item.strip() for item in items or [] if item.strip()]
