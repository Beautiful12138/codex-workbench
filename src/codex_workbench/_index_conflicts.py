from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ._index_types import _YamlRecord
from .models import ArchiveManifestState


def _record_errors(records: list[_YamlRecord]) -> list[str]:
    return [f"{record.error}: {record.relative_path}" for record in records if record.error]


def _duplicate_id_conflicts(records: list[_YamlRecord], kind: str) -> list[str]:
    seen: set[str] = set()
    conflicts: list[str] = []
    for record in records:
        if not record.data or not record.id:
            continue
        if record.id in seen:
            conflicts.append(f"duplicate_{kind}_id: {record.id}")
        seen.add(record.id)
    return conflicts


def _path_id_conflicts(records: list[_YamlRecord], kind: str) -> list[str]:
    conflicts: list[str] = []
    for record in records:
        if not record.data or not record.id:
            continue
        expected = record.path.parent.name
        if expected != record.id:
            conflicts.append(f"{kind}_id_mismatch: path={expected} yaml={record.id}")
    return conflicts


def _file_id_conflicts(records: list[_YamlRecord], kind: str) -> list[str]:
    conflicts: list[str] = []
    for record in records:
        if not record.data or not record.id:
            continue
        expected = record.path.stem
        if expected != record.id:
            conflicts.append(f"{kind}_id_mismatch: path={expected} yaml={record.id}")
    return conflicts


def _task_ref_conflicts(requirements: list[_YamlRecord], tasks: list[_YamlRecord]) -> list[str]:
    task_by_id = {record.id: record for record in tasks if record.id}
    requirement_by_id = {record.id: record for record in requirements if record.id}
    conflicts: list[str] = []
    for requirement in requirements:
        if not requirement.data:
            continue
        task_refs = requirement.data.get("task_refs", [])
        if not isinstance(task_refs, list):
            continue
        for task_ref in task_refs:
            task_id = str(task_ref).strip()
            task = task_by_id.get(task_id)
            if task is None:
                conflicts.append(f"unknown_task_ref: {requirement.id} -> {task_ref}")
                continue
            task_requirement_id = (
                str(task.data.get("requirement_id", "")).strip() if task.data else ""
            )
            if not task_requirement_id:
                conflicts.append(f"missing_task_requirement_id: {task_id}")
            elif task_requirement_id != requirement.id:
                conflicts.append(
                    f"task_requirement_mismatch: {requirement.id} -> {task_id} requirement_id={task_requirement_id}"
                )
    for task in tasks:
        if not task.data:
            continue
        task_requirement_id = str(task.data.get("requirement_id", "")).strip()
        if not task_requirement_id:
            conflicts.append(f"missing_task_requirement_id: {task.id}")
            continue
        if not task.id.startswith(f"{task_requirement_id}-"):
            conflicts.append(
                f"task_id_requirement_prefix_mismatch: {task_requirement_id} -> {task.id}"
            )
        requirement = requirement_by_id.get(task_requirement_id)
        if requirement is None:
            conflicts.append(f"unknown_requirement_ref: {task.id} -> {task_requirement_id}")
            continue
        task_refs = requirement.data.get("task_refs", []) if requirement.data else []
        if isinstance(task_refs, list) and task.id not in {str(item).strip() for item in task_refs}:
            conflicts.append(f"missing_requirement_task_ref: {task_requirement_id} -> {task.id}")
    return conflicts


def _service_ref_conflicts(tasks: list[_YamlRecord], services: list[dict[str, Any]]) -> list[str]:
    service_names = {str(item.get("name", "")).strip() for item in services if item.get("name")}
    conflicts: list[str] = []
    for task in tasks:
        if not task.data:
            continue
        refs = task.data.get("service_refs", [])
        if not isinstance(refs, list):
            continue
        for service_ref in refs:
            if str(service_ref) not in service_names:
                conflicts.append(f"unknown_service_ref: {task.id} -> {service_ref}")
    return conflicts


def _evidence_conflicts(tasks: list[_YamlRecord], evidences: list[_YamlRecord]) -> list[str]:
    evidence_by_task = {
        str(record.data.get("task_id", "")).strip(): record
        for record in evidences
        if record.data and record.data.get("task_id")
    }
    evidence_ids = {record.id for record in evidences if record.id}
    conflicts: list[str] = []
    for evidence in evidences:
        if not evidence.data:
            continue
        task_id = str(evidence.data.get("task_id", "")).strip()
        task_dir_id = evidence.path.parent.name
        if task_id and task_id != task_dir_id:
            conflicts.append(f"evidence_task_mismatch: {evidence.id} -> {task_id}")
    for task in tasks:
        if not task.data:
            continue
        validation = task.data.get("validation", {})
        if not isinstance(validation, dict):
            continue
        evidence_ref = validation.get("evidence_ref")
        if evidence_ref and str(evidence_ref) not in evidence_ids:
            conflicts.append(f"missing_evidence_ref: {task.id} -> {evidence_ref}")
        if evidence_ref and task.id not in evidence_by_task:
            conflicts.append(f"missing_task_evidence: {task.id} -> {evidence_ref}")
    return conflicts


def _archive_manifest_conflicts(archives: list[_YamlRecord]) -> list[str]:
    conflicts: list[str] = []
    for archive in archives:
        if not archive.data:
            continue
        try:
            ArchiveManifestState.model_validate(archive.data)
        except ValidationError:
            conflicts.append(f"invalid_archive_manifest: {archive.relative_path}")
    return conflicts
