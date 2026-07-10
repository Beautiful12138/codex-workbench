from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import (
    read_yaml,
    read_yaml_with_version,
    rollback_text_files_if_unchanged,
    write_text_utf8_atomic,
    write_yaml_atomic as write_yaml_atomic,
)
from .lifecycle import requirement_allows_formal_task
from .models import RequirementState, TaskStage, TaskState
from .refs import validate_package_ref
from .services import read_service_registry
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
    version: str


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

    written_contents: dict[Path, str] = {}
    try:
        for path, content in targets:
            existed_before_write = path.exists()
            write_text_utf8_atomic(path, content, dry_run=dry_run, create_only=not overwrite)
            if not existed_before_write:
                written_contents[path] = content
    except WorkbenchError:
        rollback_text_files_if_unchanged(written_contents, dry_run=dry_run)
        raise

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
) -> tuple[Path, Path, dict, TaskState, str]:
    clean_task_id = validate_package_ref(task_id)
    root = Path(workspace_root).expanduser().resolve()
    task_yaml = _package_file(root, "docs/active", clean_task_id, "task.yaml")
    snapshot = read_yaml_with_version(task_yaml)
    data = snapshot.data
    task = TaskState.model_validate(data)
    if task.id != clean_task_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={clean_task_id} actual={task.id}",
            exit_code=2,
        )
    return root, task_yaml, data, task, snapshot.version


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


def _apply_task_impact_update(
    data: dict,
    *,
    process_level: str | None,
    risk_level: str | None,
    impact_profile: dict | None,
    risk_triggers: list[str] | None,
    reason: str | None,
    require_reason: bool,
) -> None:
    cleaned_reason = (reason or "").strip()
    has_update = any(
        (
            process_level is not None,
            risk_level is not None,
            impact_profile is not None,
            risk_triggers is not None,
        )
    )
    if not has_update:
        return
    if require_reason and not cleaned_reason:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_risk_assessment_reason",
            exit_code=2,
        )
    if process_level is not None:
        data["process_level"] = process_level.strip()
    if risk_level is not None:
        data["risk_level"] = risk_level.strip()
    if impact_profile is not None:
        existing_profile = data.get("impact_profile")
        if isinstance(existing_profile, dict):
            data["impact_profile"] = {**existing_profile, **impact_profile}
        else:
            if "action" not in impact_profile:
                raise WorkbenchError(
                    ErrorCode.VALIDATION_ERROR,
                    "impact_profile_requires_action",
                    exit_code=2,
                )
            data["impact_profile"] = impact_profile
    if risk_triggers is not None:
        triggers = _clean_list(risk_triggers)
        if triggers:
            data["risk_triggers"] = triggers
    if cleaned_reason:
        notes = data.setdefault("risk_assessment_notes", [])
        if not isinstance(notes, list):
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                "invalid_risk_assessment_notes",
                exit_code=2,
            )
        notes.append(cleaned_reason)


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
    snapshot = read_yaml_with_version(requirement_yaml)
    data = snapshot.data
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
    return RequirementTaskRefUpdate(path=requirement_yaml, data=data, version=snapshot.version)


def _expected_file_contents(root: Path, files: dict[str, str]) -> dict[Path, str]:
    return {(root / rel_path): content for rel_path, content in files.items()}


def _rollback_created_files(
    paths: tuple[Path, ...],
    *,
    dry_run: bool,
    expected_contents: dict[Path, str] | None = None,
) -> None:
    if dry_run:
        return
    if expected_contents is not None:
        rollback_text_files_if_unchanged(expected_contents, dry_run=dry_run)
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
