from __future__ import annotations

from pathlib import Path

import yaml

from . import _package_core as package_core
from ._package_core import PackageWriteResult
from .errors import ErrorCode, WorkbenchError
from .lifecycle import requirement_allows_formal_task
from .models import ConfirmationType, RequirementState, TaskStage, TaskState
from .refs import validate_package_ref
from .templates import (
    RequirementTemplateContext,
    TaskTemplateContext,
    render_requirement_package,
    render_task_package,
)
from .timeutils import resolve_timestamp


def create_requirement_package(
    workspace_root: str | Path,
    context: RequirementTemplateContext,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> PackageWriteResult:
    files = render_requirement_package(context)
    requirement_yaml = yaml.safe_load(
        next(content for path, content in files.items() if path.endswith("requirement.yaml"))
    )
    RequirementState.model_validate(requirement_yaml)
    return package_core.write_package_files(
        workspace_root, files, dry_run=dry_run, overwrite=overwrite
    )


def create_task_package(
    workspace_root: str | Path,
    context: TaskTemplateContext,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> PackageWriteResult:
    package_core._validate_new_package_id(context.task_id)
    validate_package_ref(context.requirement_id)
    try:
        stage = TaskStage(context.stage)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_stage: {context.stage}",
            exit_code=2,
        ) from exc
    if stage in package_core.FINAL_CREATE_STAGES:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"final_stage_not_allowed: {stage.value}",
            exit_code=2,
        )
    if stage not in package_core.INITIAL_CREATE_STAGES:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"initial_stage_not_allowed: {stage.value}",
            exit_code=2,
        )

    root = Path(workspace_root).expanduser().resolve()
    package_core._assert_task_id_matches_requirement(context.requirement_id, context.task_id)
    requirement_update = package_core._prepare_requirement_task_ref_update(
        root,
        context.requirement_id,
        context.task_id,
    )
    files = render_task_package(context)
    task_yaml = yaml.safe_load(
        next(content for path, content in files.items() if path.endswith("task.yaml"))
    )
    TaskState.model_validate(task_yaml)
    result = package_core.write_package_files(
        workspace_root, files, dry_run=dry_run, overwrite=overwrite
    )
    try:
        package_core.write_yaml_atomic(
            requirement_update.path,
            requirement_update.data,
            dry_run=dry_run,
            expected_version=requirement_update.version,
        )
    except WorkbenchError:
        package_core._rollback_created_files(
            result.paths,
            dry_run=dry_run,
            expected_contents=package_core._expected_file_contents(root, files),
        )
        raise
    return package_core.PackageWriteResult(
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
    path = package_core._package_file(root, "docs/active", clean_requirement_id, "requirement.yaml")
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {clean_requirement_id}",
            exit_code=2,
        )

    snapshot = package_core.read_yaml_with_version(path)
    data = snapshot.data
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
        isinstance(item, dict) and item.get("type") == ConfirmationType.REQUIREMENT_CLOSURE.value
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
    data["updated_at"] = resolve_timestamp(updated_at)
    RequirementState.model_validate(data)
    package_core.write_yaml_atomic(path, data, dry_run=dry_run, expected_version=snapshot.version)
    return package_core.PackageWriteResult(paths=(path,), dry_run=dry_run)
