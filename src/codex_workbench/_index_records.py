from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ._index_conflicts import (
    _archive_manifest_conflicts,
    _duplicate_id_conflicts,
    _evidence_conflicts,
    _file_id_conflicts,
    _path_id_conflicts,
    _record_errors,
    _service_ref_conflicts,
    _task_ref_conflicts,
)
from ._index_types import _IndexSnapshot, _YamlRecord


def collect_snapshot(root: Path) -> _IndexSnapshot:
    requirements = _read_records(root, "docs/active/*/requirement.yaml", "requirement")
    tasks = _read_records(root, "docs/active/*/task.yaml", "task")
    evidences = _read_records(root, "docs/active/*/evidence.yaml", "evidence")
    archives = _read_records(root, "docs/archive/*/archive.yaml", "archive")
    discoveries = _read_records(root, "docs/inbox/*/discovery.yaml", "discovery")
    actions = _read_records(root, "docs/actions/*.yaml", "action")
    changes = _read_records(root, "docs/changes/*.yaml", "change")
    decisions = _read_records(root, "docs/decisions/*.yaml", "decision")
    suspicions = _read_records(root, "docs/suspicions/*.yaml", "suspicion")
    services, service_conflicts = _read_services(root)
    materials, material_conflicts = _read_materials(root)

    conflicts = [
        *service_conflicts,
        *material_conflicts,
        *_record_errors(requirements),
        *_record_errors(tasks),
        *_record_errors(evidences),
        *_record_errors(archives),
        *_archive_manifest_conflicts(archives),
        *_record_errors(discoveries),
        *_record_errors(actions),
        *_record_errors(changes),
        *_record_errors(decisions),
        *_record_errors(suspicions),
        *_path_id_conflicts(requirements, "requirement"),
        *_path_id_conflicts(tasks, "task"),
        *_path_id_conflicts(discoveries, "discovery"),
        *_file_id_conflicts(actions, "action"),
        *_file_id_conflicts(changes, "change"),
        *_file_id_conflicts(decisions, "decision"),
        *_file_id_conflicts(suspicions, "suspicion"),
        *_duplicate_id_conflicts(requirements, "requirement"),
        *_duplicate_id_conflicts(tasks, "task"),
        *_duplicate_id_conflicts(evidences, "evidence"),
        *_duplicate_id_conflicts(actions, "action"),
        *_duplicate_id_conflicts(changes, "change"),
        *_duplicate_id_conflicts(decisions, "decision"),
        *_duplicate_id_conflicts(suspicions, "suspicion"),
    ]
    conflicts.extend(_task_ref_conflicts(requirements, tasks))
    conflicts.extend(_service_ref_conflicts(tasks, services))
    conflicts.extend(_evidence_conflicts(tasks, evidences))
    return _IndexSnapshot(
        requirements=[record for record in requirements if record.data],
        tasks=[record for record in tasks if record.data],
        evidences=[record for record in evidences if record.data],
        archives=[record for record in archives if record.data],
        materials=materials,
        discoveries=[record for record in discoveries if record.data],
        services=services,
        actions=[record for record in actions if record.data],
        changes=[record for record in changes if record.data],
        decisions=[record for record in decisions if record.data],
        suspicions=[record for record in suspicions if record.data],
        conflicts=sorted(dict.fromkeys(conflicts)),
    )


def _read_records(root: Path, pattern: str, kind: str) -> list[_YamlRecord]:
    records: list[_YamlRecord] = []
    for path in sorted(root.glob(pattern), key=lambda item: item.as_posix()):
        relative_path = path.relative_to(root).as_posix()
        try:
            data = _load_yaml_dict(path)
        except yaml.YAMLError:
            records.append(
                _YamlRecord(
                    kind=kind,
                    path=path,
                    relative_path=relative_path,
                    data=None,
                    error="invalid_yaml",
                )
            )
            continue
        if data is None:
            continue
        if not isinstance(data, dict):
            records.append(
                _YamlRecord(
                    kind=kind,
                    path=path,
                    relative_path=relative_path,
                    data=None,
                    error="invalid_yaml",
                )
            )
            continue
        records.append(_YamlRecord(kind=kind, path=path, relative_path=relative_path, data=data))
    return records


def _read_materials(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / "docs" / "inbox" / "materials.yaml"
    if not path.exists():
        return [], []
    try:
        data = _load_yaml_dict(path)
    except yaml.YAMLError:
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    if not isinstance(data, dict):
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    materials = data.get("materials", [])
    if not isinstance(materials, list):
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    return [item for item in materials if isinstance(item, dict)], []


def _read_services(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / "services" / "registry.yaml"
    if not path.exists():
        return [], [f"missing: {path.relative_to(root).as_posix()}"]
    try:
        data = _load_yaml_dict(path)
    except yaml.YAMLError:
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    if not isinstance(data, dict):
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    services = data.get("services", [])
    if not isinstance(services, list):
        return [], [f"invalid_yaml: {path.relative_to(root).as_posix()}"]
    return [item for item in services if isinstance(item, dict)], []


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return {} if data is None else data
