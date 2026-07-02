from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .doctor import run_doctor
from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, write_yaml_atomic
from .lifecycle import evaluate_archive_task
from .models import (
    CURRENT_SCHEMA_VERSION,
    ArchiveManifestState,
    ConfirmationType,
    RequirementState,
    TaskStage,
    TaskState,
)
from .refs import validate_package_ref
from .validation import assert_done_evidence_valid
from .workspace import resolve_workspace_path


@dataclass(frozen=True)
class ArchivePlanEntry:
    source_kind: str
    source_id: str
    source_path: Path
    archive_path: Path
    reason: str


@dataclass(frozen=True)
class ArchivePlan:
    version: str
    requirement_ids: tuple[str, ...]
    archived_at: str
    archive_authorization_note: str
    manifest_path: Path
    entries: tuple[ArchivePlanEntry, ...]
    doctor_warnings: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool
    plan: ArchivePlan


@dataclass(frozen=True)
class ArchiveSummary:
    version: str
    archived_at: str
    requirement_ids: tuple[str, ...]
    path: Path


def list_archive_versions(workspace_root: str | Path) -> tuple[ArchiveSummary, ...]:
    root = Path(workspace_root).expanduser().resolve()
    summaries: list[ArchiveSummary] = []
    for path in sorted((root / "docs" / "archive").glob("*/archive.yaml")):
        try:
            manifest = ArchiveManifestState.model_validate(read_yaml(path))
        except (ValidationError, WorkbenchError) as exc:
            relative_path = path.relative_to(root).as_posix()
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"invalid_archive_manifest: {relative_path}",
                exit_code=2,
            ) from exc
        summaries.append(
            ArchiveSummary(
                version=manifest.version,
                archived_at=manifest.archived_at,
                requirement_ids=tuple(manifest.requirement_ids),
                path=path,
            )
        )
    return tuple(summaries)


def plan_version_archive(
    workspace_root: str | Path,
    *,
    version: str,
    requirement_ids: list[str],
    archive_authorization_note: str,
    archived_at: str,
) -> ArchivePlan:
    root = Path(workspace_root).expanduser().resolve()
    authorization_note = archive_authorization_note.strip()
    if not authorization_note:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_archive_authorization",
            exit_code=2,
        )
    clean_version = _validate_archive_version(version)
    clean_requirement_ids = _validate_requirement_ids(requirement_ids)

    entries: list[ArchivePlanEntry] = []
    for requirement_id in clean_requirement_ids:
        requirement = _read_requirement(root, requirement_id)
        if not _has_confirmation(requirement, ConfirmationType.REQUIREMENT_CLOSURE):
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"missing_requirement_closure: {requirement_id}",
                exit_code=2,
            )
        entries.append(
            _plan_entry(
                root,
                version=clean_version,
                source_kind="requirement",
                source_id=requirement_id,
                reason="requirement_version_archive",
            )
        )
        for task_id in _clean_task_refs(requirement.task_refs):
            task = _read_task(root, task_id)
            _assert_task_archiveable(root, task)
            entries.append(
                _plan_entry(
                    root,
                    version=clean_version,
                    source_kind="task",
                    source_id=task_id,
                    reason="requirement_task_version_archive",
                )
            )

    _assert_no_duplicate_entries(root, entries)
    doctor_report = run_doctor(root)
    if doctor_report.blockings:
        codes = ",".join(finding.code for finding in doctor_report.blockings)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"doctor_blocking: {codes}",
            exit_code=2,
        )

    manifest_path = resolve_workspace_path(root, f"docs/archive/{clean_version}/archive.yaml")
    _assert_archive_targets_available(root, manifest_path, entries)
    return ArchivePlan(
        version=clean_version,
        requirement_ids=tuple(clean_requirement_ids),
        archived_at=archived_at,
        archive_authorization_note=authorization_note,
        manifest_path=manifest_path,
        entries=tuple(entries),
        doctor_warnings=tuple(finding.code for finding in doctor_report.warnings),
    )


def archive_version(
    workspace_root: str | Path,
    *,
    version: str,
    requirement_ids: list[str],
    archive_authorization_note: str,
    archived_at: str,
    dry_run: bool = False,
) -> ArchiveWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    plan = plan_version_archive(
        root,
        version=version,
        requirement_ids=requirement_ids,
        archive_authorization_note=archive_authorization_note,
        archived_at=archived_at,
    )
    paths = (plan.manifest_path, *(entry.archive_path for entry in plan.entries))
    if dry_run:
        return ArchiveWriteResult(paths=paths, dry_run=True, plan=plan)

    manifest_payload = _manifest_payload(root, plan)
    moved_entries: list[tuple[Path, Path]] = []
    try:
        for entry in plan.entries:
            entry.archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry.source_path), str(entry.archive_path))
            moved_entries.append((entry.archive_path, entry.source_path))
        write_yaml_atomic(plan.manifest_path, manifest_payload)
    except Exception as exc:
        _rollback_archive_move(moved_entries, plan.manifest_path)
        if isinstance(exc, WorkbenchError):
            raise
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"archive_write_failed: {exc}",
            exit_code=1,
        ) from exc
    return ArchiveWriteResult(paths=paths, dry_run=False, plan=plan)


def _validate_archive_version(version: str) -> str:
    cleaned = version.strip()
    parts = Path(cleaned).parts
    if (
        not cleaned
        or cleaned != version
        or parts != (cleaned,)
        or cleaned in {".", ".."}
    ):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_archive_version: {version}",
            exit_code=2,
        )
    return cleaned


def _validate_requirement_ids(requirement_ids: list[str]) -> list[str]:
    cleaned = [validate_package_ref(item) for item in requirement_ids]
    if not cleaned:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_requirement_ids",
            exit_code=2,
        )
    return cleaned


def _read_requirement(root: Path, requirement_id: str) -> RequirementState:
    path = resolve_workspace_path(root, f"docs/active/{requirement_id}/requirement.yaml")
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {requirement_id}",
            exit_code=2,
        )
    try:
        requirement = RequirementState.model_validate(read_yaml(path))
    except (ValidationError, WorkbenchError) as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_requirement_package: {requirement_id}",
            exit_code=2,
        ) from exc
    if requirement.id != requirement_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_id_mismatch: expected={requirement_id} actual={requirement.id}",
            exit_code=2,
        )
    return requirement


def _read_task(root: Path, task_id: str) -> TaskState:
    path = resolve_workspace_path(root, f"docs/active/{task_id}/task.yaml")
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_task_package: {task_id}",
            exit_code=2,
        )
    try:
        task = TaskState.model_validate(read_yaml(path))
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


def _assert_task_archiveable(root: Path, task: TaskState) -> None:
    check = evaluate_archive_task(task)
    if not check.allowed:
        reasons = ",".join(check.reason_codes)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"archive_preflight_blocked: {task.id} {reasons}",
            exit_code=2,
        )
    if task.stage is TaskStage.DONE:
        try:
            assert_done_evidence_valid(root, task)
        except WorkbenchError as exc:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"archive_preflight_blocked: {task.id} {exc.message}",
                exit_code=2,
            ) from exc


def _has_confirmation(requirement: RequirementState, confirmation_type: ConfirmationType) -> bool:
    return any(item.type is confirmation_type for item in requirement.confirmations)


def _clean_task_refs(task_refs: list[str]) -> list[str]:
    return [validate_package_ref(item) for item in task_refs]


def _plan_entry(
    root: Path,
    *,
    version: str,
    source_kind: str,
    source_id: str,
    reason: str,
) -> ArchivePlanEntry:
    source_path = resolve_workspace_path(root, f"docs/active/{source_id}")
    if not source_path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_{source_kind}_package: {source_id}",
            exit_code=2,
        )
    archive_path = resolve_workspace_path(root, f"docs/archive/{version}/{source_id}")
    return ArchivePlanEntry(
        source_kind=source_kind,
        source_id=source_id,
        source_path=source_path,
        archive_path=archive_path,
        reason=reason,
    )


def _assert_archive_targets_available(
    root: Path,
    manifest_path: Path,
    entries: list[ArchivePlanEntry],
) -> None:
    if manifest_path.exists():
        _raise_target_exists(root, manifest_path)
    for entry in entries:
        if entry.archive_path.exists():
            _raise_target_exists(root, entry.archive_path)
    version_dir = manifest_path.parent
    if version_dir.exists() and any(version_dir.iterdir()):
        relative_path = version_dir.relative_to(root).as_posix()
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"archive_version_directory_not_empty: {relative_path}",
            exit_code=2,
        )


def _assert_no_duplicate_entries(root: Path, entries: list[ArchivePlanEntry]) -> None:
    seen: set[tuple[str, str]] = set()
    seen_archive_paths: set[str] = set()
    for entry in entries:
        key = (entry.source_kind, entry.source_id)
        if key in seen:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"duplicate_archive_source: {entry.source_kind} {entry.source_id}",
                exit_code=2,
            )
        seen.add(key)
        archive_path = entry.archive_path.relative_to(root).as_posix()
        if archive_path in seen_archive_paths:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"duplicate_archive_path: {archive_path}",
                exit_code=2,
            )
        seen_archive_paths.add(archive_path)


def _raise_target_exists(root: Path, path: Path) -> None:
    relative_path = path.relative_to(root).as_posix()
    raise WorkbenchError(
        ErrorCode.VALIDATION_ERROR,
        f"archive_target_exists: {relative_path}",
        exit_code=2,
    )


def _rollback_archive_move(moved_entries: list[tuple[Path, Path]], manifest_path: Path) -> None:
    if manifest_path.exists():
        manifest_path.unlink()
    for archive_path, source_path in reversed(moved_entries):
        if archive_path.exists() and not source_path.exists():
            source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(archive_path), str(source_path))


def _manifest_payload(root: Path, plan: ArchivePlan) -> dict[str, object]:
    payload = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "version": plan.version,
        "archived_at": plan.archived_at,
        "requirement_ids": list(plan.requirement_ids),
        "authorization": {
            "type": ConfirmationType.ARCHIVE_AUTHORIZATION.value,
            "source": "user",
            "note": plan.archive_authorization_note,
        },
        "entries": [
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "id": f"ARCHIVE-{plan.version}-{entry.source_id}",
                "version": plan.version,
                "source_kind": entry.source_kind,
                "source_id": entry.source_id,
                "source_path": entry.source_path.relative_to(root).as_posix(),
                "archive_path": entry.archive_path.relative_to(root).as_posix(),
                "reason": entry.reason,
                "archived_at": plan.archived_at,
                "preflight_summary": list(plan.doctor_warnings),
            }
            for entry in plan.entries
        ],
    }
    ArchiveManifestState.model_validate(payload)
    return payload
