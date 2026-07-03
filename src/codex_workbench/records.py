from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import rollback_text_files_if_unchanged, write_text_utf8_atomic
from .models import (
    ActionStatus,
    ActionNoteState,
    ChangeKind,
    ChangeRecordState,
    CURRENT_SCHEMA_VERSION,
    DecisionState,
    SuspicionState,
)
from .refs import validate_package_ref
from .templates import (
    ActionNoteTemplateContext,
    ChangeRecordTemplateContext,
    DecisionRecordTemplateContext,
    SuspicionTemplateContext,
    TemplateError,
    render_action_note,
    render_change_record,
    render_decision_record,
    render_suspicion_log,
)


@dataclass(frozen=True)
class RecordWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool


@dataclass(frozen=True)
class ChangeClassification:
    kind: ChangeKind
    requires_change_record: bool
    reason_code: str


def classify_change(*, kind: str, summary: str) -> ChangeClassification:
    summary = summary.strip()
    if not summary:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, "missing_change_summary", exit_code=2)
    try:
        change_kind = ChangeKind(kind)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_change_kind: {kind}",
            exit_code=2,
        ) from exc
    if change_kind is ChangeKind.IMPLEMENTATION_ADJUSTMENT:
        return ChangeClassification(
            kind=change_kind,
            requires_change_record=False,
            reason_code="no_formal_change_record",
        )
    if change_kind is ChangeKind.SCOPE_CLARIFICATION:
        return ChangeClassification(
            kind=change_kind,
            requires_change_record=False,
            reason_code="scope_alignment_required",
        )
    return ChangeClassification(
        kind=change_kind,
        requires_change_record=True,
        reason_code="change_control_required",
    )


def create_action_note(
    workspace_root: str | Path,
    *,
    action_id: str,
    title: str,
    summary: str,
    action_type: str,
    updated_at: str,
    status: str = ActionStatus.EXECUTED.value,
    authorization: str | None = None,
    target: str | None = None,
    result: str | None = None,
    related_refs: list[str] | None = None,
    side_effect_summary: str = "no_side_effect",
    rollback_hint: str = "no_rollback_needed",
    dry_run: bool = False,
    overwrite: bool = False,
) -> RecordWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    action_id = validate_package_ref(action_id)
    related_refs = [validate_package_ref(item) for item in _clean_list(related_refs)]

    try:
        action = ActionNoteState(
            schema_version=CURRENT_SCHEMA_VERSION,
            id=action_id,
            title=title,
            updated_at=updated_at,
            summary=summary,
            action_type=action_type,
            status=status,
            authorization=authorization.strip() if authorization and authorization.strip() else None,
            target=target.strip() if target and target.strip() else None,
            result=result.strip() if result and result.strip() else None,
            related_refs=related_refs,
            side_effect_summary=side_effect_summary,
            rollback_hint=rollback_hint,
        )
        files = render_action_note(
            ActionNoteTemplateContext(
                action_id=action.id,
                title=action.title,
                summary=action.summary,
                action_type=action.action_type.value,
                status=action.status.value,
                authorization=action.authorization,
                target=action.target,
                result=action.result,
                related_refs=action.related_refs,
                side_effect_summary=action.side_effect_summary,
                rollback_hint=action.rollback_hint,
                updated_at=action.updated_at,
            )
        )
    except (TemplateError, ValidationError) as exc:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, str(exc), exit_code=2) from exc

    return _write_record_files(root, files, dry_run=dry_run, overwrite=overwrite)


def create_change_record(
    workspace_root: str | Path,
    *,
    change_id: str,
    title: str,
    changed_area: str,
    reason: str,
    impact: str,
    handling: str,
    updated_at: str,
    related_refs: list[str] | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> RecordWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    change_id = validate_package_ref(change_id)
    related_refs = [validate_package_ref(item) for item in _clean_list(related_refs)]

    try:
        record = ChangeRecordState(
            schema_version=CURRENT_SCHEMA_VERSION,
            id=change_id,
            title=title,
            updated_at=updated_at,
            change_kind=ChangeKind.SCOPE_CHANGE,
            changed_area=changed_area,
            reason=reason,
            impact=impact,
            handling=handling,
            related_refs=related_refs,
        )
        files = render_change_record(
            ChangeRecordTemplateContext(
                change_id=record.id,
                title=record.title,
                updated_at=record.updated_at,
                change_kind=record.change_kind.value,
                changed_area=record.changed_area,
                reason=record.reason,
                impact=record.impact,
                handling=record.handling,
                related_refs=record.related_refs,
            )
        )
    except (TemplateError, ValidationError) as exc:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, str(exc), exit_code=2) from exc

    return _write_record_files(root, files, dry_run=dry_run, overwrite=overwrite)


def create_decision_record(
    workspace_root: str | Path,
    *,
    decision_id: str,
    title: str,
    cold_path_reason: str,
    context: str,
    decision: str,
    impact: str,
    updated_at: str,
    dry_run: bool = False,
    overwrite: bool = False,
) -> RecordWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    decision_id = validate_package_ref(decision_id)
    try:
        record = DecisionState(
            schema_version=CURRENT_SCHEMA_VERSION,
            id=decision_id,
            title=title,
            updated_at=updated_at,
            cold_path_reason=cold_path_reason,
            context=context,
            decision=decision,
            impact=impact,
        )
        files = render_decision_record(
            DecisionRecordTemplateContext(
                decision_id=record.id,
                title=record.title,
                updated_at=record.updated_at,
                cold_path_reason=record.cold_path_reason,
                context=record.context,
                decision=record.decision,
                impact=record.impact,
                status=record.status,
            )
        )
    except (TemplateError, ValidationError) as exc:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, str(exc), exit_code=2) from exc

    return _write_record_files(root, files, dry_run=dry_run, overwrite=overwrite)


def create_suspicion_log(
    workspace_root: str | Path,
    *,
    suspicion_id: str,
    title: str,
    location_or_subject: str,
    confirmed_facts: list[str],
    ai_inferences: list[str],
    current_task_impact: str,
    suggested_handling: str,
    updated_at: str,
    assumptions: list[str] | None = None,
    related_refs: list[str] | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> RecordWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    suspicion_id = validate_package_ref(suspicion_id)
    related_refs = [validate_package_ref(item) for item in _clean_list(related_refs)]
    confirmed_facts = _clean_list(confirmed_facts)
    ai_inferences = _clean_list(ai_inferences)
    assumptions = _clean_list(assumptions)
    try:
        record = SuspicionState(
            schema_version=CURRENT_SCHEMA_VERSION,
            id=suspicion_id,
            title=title,
            updated_at=updated_at,
            location_or_subject=location_or_subject,
            confirmed_facts=confirmed_facts,
            ai_inferences=ai_inferences,
            assumptions=assumptions,
            current_task_impact=current_task_impact,
            suggested_handling=suggested_handling,
            related_refs=related_refs,
        )
        files = render_suspicion_log(
            SuspicionTemplateContext(
                suspicion_id=record.id,
                title=record.title,
                updated_at=record.updated_at,
                location_or_subject=record.location_or_subject,
                confirmed_facts=record.confirmed_facts,
                ai_inferences=record.ai_inferences,
                assumptions=record.assumptions,
                current_task_impact=record.current_task_impact,
                suggested_handling=record.suggested_handling,
                related_refs=record.related_refs,
            )
        )
    except (TemplateError, ValidationError) as exc:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, str(exc), exit_code=2) from exc

    return _write_record_files(root, files, dry_run=dry_run, overwrite=overwrite)


def _write_record_files(
    root: Path,
    files: dict[str, str],
    *,
    dry_run: bool,
    overwrite: bool,
) -> RecordWriteResult:
    targets = tuple((root / rel_path, content) for rel_path, content in files.items())
    if not overwrite:
        for path, _ in targets:
            if path.exists():
                raise WorkbenchError(
                    ErrorCode.VALIDATION_ERROR,
                    f"already_exists: {path.relative_to(root).as_posix()}",
                    exit_code=2,
                )
    written_contents: dict[Path, str] = {}
    try:
        for path, content in targets:
            existed_before_write = path.exists()
            write_text_utf8_atomic(
                path,
                content,
                dry_run=dry_run,
                create_only=not overwrite,
            )
            if not existed_before_write:
                written_contents[path] = content
    except WorkbenchError:
        rollback_text_files_if_unchanged(written_contents, dry_run=dry_run)
        raise
    return RecordWriteResult(paths=tuple(path for path, _ in targets), dry_run=dry_run)


def _clean_list(items: list[str] | None) -> list[str]:
    return [item.strip() for item in items or [] if item.strip()]
