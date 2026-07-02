from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, write_yaml_atomic
from .models import (
    CURRENT_SCHEMA_VERSION,
    DiscoveryState,
    Knowledge,
    MaterialEntry,
    MaterialRegistry,
    RequirementReadinessStatus,
    RequirementState,
)
from .packages import PackageWriteResult, create_requirement_package, write_package_files
from .templates import RequirementTemplateContext
from .timeutils import resolve_timestamp
from .workspace import resolve_workspace_path


MATERIALS_REGISTRY = "docs/inbox/materials.yaml"


@dataclass(frozen=True)
class RegistryWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool


def read_material_registry(workspace_root: str | Path) -> MaterialRegistry:
    path = _materials_registry_path(workspace_root)
    if not path.exists():
        return MaterialRegistry(schema_version=CURRENT_SCHEMA_VERSION, materials=[])
    return MaterialRegistry.model_validate(read_yaml(path))


def add_material(
    workspace_root: str | Path,
    *,
    material_id: str,
    title: str,
    source: str,
    summary: str,
    received_at: str,
    sensitivity: str = "low",
    large_file: bool = False,
    original_location: str | None = None,
    committable_original: bool = False,
    related_refs: list[str] | None = None,
    retention: str | None = None,
    dry_run: bool = False,
) -> RegistryWriteResult:
    path = _materials_registry_path(workspace_root)
    registry = read_material_registry(workspace_root)
    if any(entry.id == material_id for entry in registry.materials):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"already_exists: {material_id}",
            exit_code=2,
        )
    entry = MaterialEntry(
        id=material_id,
        title=title,
        source=source,
        received_at=received_at,
        summary=summary,
        sensitivity=sensitivity,
        large_file=large_file,
        original_location=original_location,
        committable_original=committable_original,
        related_refs=related_refs or [],
        retention=retention,
    )
    payload = registry.model_dump(mode="json")
    payload["materials"].append(entry.model_dump(mode="json"))
    write_yaml_atomic(path, payload, dry_run=dry_run)
    return RegistryWriteResult(paths=(path,), dry_run=dry_run)


def create_discovery_package(
    workspace_root: str | Path,
    *,
    discovery_id: str,
    title: str,
    material_refs: list[str],
    updated_at: str,
    confirmed_facts: list[str] | None = None,
    system_observations: list[str] | None = None,
    ai_inferences: list[str] | None = None,
    assumptions: list[str] | None = None,
    questions_for_user: list[str] | None = None,
    dry_run: bool = False,
) -> PackageWriteResult:
    _validate_package_ref(discovery_id)
    material_refs = _clean_list(material_refs)
    if not material_refs:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_material_ref",
            exit_code=2,
        )
    _ensure_material_refs_known(workspace_root, material_refs)
    discovery = DiscoveryState(
        schema_version=CURRENT_SCHEMA_VERSION,
        id=discovery_id,
        title=title,
        material_refs=material_refs,
        updated_at=updated_at,
        knowledge=_knowledge(
            confirmed_facts=confirmed_facts,
            system_observations=system_observations,
            ai_inferences=ai_inferences,
            assumptions=assumptions,
            questions_for_user=questions_for_user,
        ),
    )
    base = f"docs/inbox/{discovery_id}"
    files = {
        f"{base}/discovery.yaml": yaml.safe_dump(
            discovery.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        ),
        f"{base}/discovery.md": _render_discovery_markdown(discovery),
    }
    return write_package_files(workspace_root, files, dry_run=dry_run)


def create_intake_draft(
    workspace_root: str | Path,
    context: RequirementTemplateContext,
    *,
    dry_run: bool = False,
) -> PackageWriteResult:
    _validate_package_ref(context.requirement_id)
    if not _clean_list(context.material_refs) and not _clean_list(context.discovery_refs):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_intake_source_refs",
            exit_code=2,
        )
    _ensure_material_refs_known(workspace_root, _clean_list(context.material_refs))
    _ensure_discovery_refs_valid(workspace_root, _clean_list(context.discovery_refs))
    intake_context = RequirementTemplateContext(
        requirement_id=context.requirement_id,
        title=context.title,
        goal=context.goal,
        acceptance=context.acceptance,
        created_at=context.created_at,
        updated_at=context.updated_at,
        non_goals=context.non_goals,
        task_refs=context.task_refs,
        readiness_status=RequirementReadinessStatus.INTAKE_DRAFT.value,
        readiness_confirmed_by_user=False,
        material_refs=context.material_refs,
        discovery_refs=context.discovery_refs,
        confirmed_facts=context.confirmed_facts,
        system_observations=context.system_observations,
        ai_inferences=context.ai_inferences,
        assumptions=context.assumptions,
        questions_for_user=context.questions_for_user,
    )
    return create_requirement_package(workspace_root, intake_context, dry_run=dry_run)


def confirm_intake(
    workspace_root: str | Path,
    requirement_id: str,
    *,
    updated_at: str | None = None,
    dry_run: bool = False,
) -> RegistryWriteResult:
    _validate_package_ref(requirement_id)
    path = _requirement_yaml_path(workspace_root, requirement_id)
    if not path.exists():
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"missing_requirement_package: {requirement_id}",
            exit_code=2,
        )
    data = read_yaml(path)
    requirement = RequirementState.model_validate(data)
    if requirement.readiness.status is not RequirementReadinessStatus.INTAKE_DRAFT:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"intake_not_confirmable: {requirement.readiness.status.value}",
            exit_code=2,
        )
    material_refs = _clean_list(requirement.readiness.material_refs)
    discovery_refs = _clean_list(requirement.readiness.discovery_refs)
    if not material_refs and not discovery_refs:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            "missing_intake_source_refs",
            exit_code=2,
        )
    _ensure_material_refs_known(workspace_root, material_refs)
    _ensure_discovery_refs_valid(workspace_root, discovery_refs)
    readiness = data.setdefault("readiness", {})
    readiness["status"] = RequirementReadinessStatus.READABLE.value
    readiness["confirmed_by_user"] = True
    readiness["material_refs"] = material_refs
    readiness["discovery_refs"] = discovery_refs
    data["updated_at"] = resolve_timestamp(updated_at)
    write_yaml_atomic(path, data, dry_run=dry_run)
    return RegistryWriteResult(paths=(path,), dry_run=dry_run)


def _materials_registry_path(workspace_root: str | Path) -> Path:
    return resolve_workspace_path(workspace_root, MATERIALS_REGISTRY)


def _requirement_yaml_path(workspace_root: str | Path, requirement_id: str) -> Path:
    _validate_package_ref(requirement_id)
    return resolve_workspace_path(workspace_root, f"docs/active/{requirement_id}/requirement.yaml")


def _discovery_yaml_path(workspace_root: str | Path, discovery_id: str) -> Path:
    _validate_package_ref(discovery_id)
    return resolve_workspace_path(workspace_root, f"docs/inbox/{discovery_id}/discovery.yaml")


def _ensure_material_refs_known(workspace_root: str | Path, material_refs: list[str]) -> None:
    if not material_refs:
        return
    registry = read_material_registry(workspace_root)
    known = {entry.id for entry in registry.materials}
    unknown = [material_ref for material_ref in material_refs if material_ref not in known]
    if unknown:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"unknown_material_ref: {unknown[0]}",
            exit_code=2,
        )


def _ensure_discovery_refs_valid(workspace_root: str | Path, discovery_refs: list[str]) -> None:
    for discovery_ref in discovery_refs:
        _validate_package_ref(discovery_ref)
        path = _discovery_yaml_path(workspace_root, discovery_ref)
        if not path.exists():
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"unknown_discovery_ref: {discovery_ref}",
                exit_code=2,
            )
        try:
            discovery = DiscoveryState.model_validate(read_yaml(path))
        except (ValidationError, WorkbenchError) as exc:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"invalid_discovery_ref: {discovery_ref}",
                exit_code=2,
            ) from exc
        if not _clean_list(discovery.material_refs):
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"discovery_without_material_refs: {discovery_ref}",
                exit_code=2,
            )
        _ensure_material_refs_known(workspace_root, _clean_list(discovery.material_refs))


def _knowledge(
    *,
    confirmed_facts: list[str] | None = None,
    system_observations: list[str] | None = None,
    ai_inferences: list[str] | None = None,
    assumptions: list[str] | None = None,
    questions_for_user: list[str] | None = None,
) -> Knowledge:
    return Knowledge(
        confirmed_facts=_clean_list(confirmed_facts),
        system_observations=_clean_list(system_observations),
        ai_inferences=_clean_list(ai_inferences),
        assumptions=_clean_list(assumptions),
        questions_for_user=_clean_list(questions_for_user),
    )


def _clean_list(items: list[str] | None) -> list[str]:
    return [item.strip() for item in items or [] if item.strip()]


def _validate_package_ref(package_ref: str) -> None:
    cleaned = package_ref.strip()
    parts = Path(cleaned).parts
    if (
        not cleaned
        or cleaned != package_ref
        or parts != (cleaned,)
        or cleaned == "."
    ):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_package_ref: {package_ref}",
            exit_code=2,
        )


def _render_discovery_markdown(discovery: DiscoveryState) -> str:
    lines = [
        f"# {discovery.id} {discovery.title}",
        "",
        f"updated_at: {discovery.updated_at}",
        "",
        "## Material Refs",
        "",
        *[f"- {material_ref}" for material_ref in discovery.material_refs],
    ]
    sections = [
        ("Confirmed Facts", discovery.knowledge.confirmed_facts),
        ("System Observations", discovery.knowledge.system_observations),
        ("AI Inferences", discovery.knowledge.ai_inferences),
        ("Assumptions", discovery.knowledge.assumptions),
        ("Questions For User", discovery.knowledge.questions_for_user),
    ]
    for title, items in sections:
        if items:
            lines.extend(["", f"## {title}", "", *[f"- {item}" for item in items]])
    return "\n".join(lines).rstrip() + "\n"
