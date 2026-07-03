from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .io import read_text_utf8, write_text_utf8_atomic
from .models import ArchiveManifestState, TaskState
from .risk import impact_summary, risk_gap_summary, risk_level_summary
from .workspace import resolve_workspace_path


INDEX_PATH = "docs/generated/index.md"
RECOVERY_PATH = "docs/generated/recovery.md"
CURRENT_PATH = "CURRENT.md"
CURRENT_TASK_LIMIT = 5
CURRENT_WAITING_FEEDBACK_LIMIT = 3
RECOVERY_TASK_LIMIT = 3
RECOVERY_REQUIREMENT_LIMIT = 5
RECOVERY_EVIDENCE_LIMIT = 5
RECOVERY_CONFLICT_LIMIT = 5
REDACT_MARKERS = ("token=", "password=", "secret=", "api_key=", "apikey=")


@dataclass(frozen=True)
class IndexWriteResult:
    paths: tuple[Path, ...]
    dry_run: bool
    current_text: str
    index_text: str
    recovery_text: str
    conflicts: list[str]


@dataclass(frozen=True)
class IndexCheckResult:
    clean: bool
    status: str
    messages: list[str]
    conflicts: list[str]


@dataclass(frozen=True)
class _YamlRecord:
    kind: str
    path: Path
    relative_path: str
    data: dict[str, Any] | None
    error: str | None = None

    @property
    def id(self) -> str:
        if not self.data:
            return ""
        value = self.data.get("id", "")
        return str(value).strip() if value is not None else ""

    @property
    def title(self) -> str:
        if not self.data:
            return ""
        value = self.data.get("title", "")
        return str(value).strip() if value is not None else ""


@dataclass(frozen=True)
class _IndexSnapshot:
    requirements: list[_YamlRecord]
    tasks: list[_YamlRecord]
    evidences: list[_YamlRecord]
    archives: list[_YamlRecord]
    materials: list[dict[str, Any]]
    discoveries: list[_YamlRecord]
    services: list[dict[str, Any]]
    actions: list[_YamlRecord]
    changes: list[_YamlRecord]
    decisions: list[_YamlRecord]
    suspicions: list[_YamlRecord]
    conflicts: list[str]


def generate_index_views(
    workspace_root: str | Path,
    *,
    dry_run: bool = False,
) -> IndexWriteResult:
    root = Path(workspace_root).expanduser().resolve()
    snapshot = _collect_snapshot(root)
    current_text = _render_current(snapshot)
    index_text = _render_index(snapshot)
    recovery_text = _render_recovery(snapshot)
    current_path = resolve_workspace_path(root, CURRENT_PATH)
    index_path = resolve_workspace_path(root, INDEX_PATH)
    recovery_path = resolve_workspace_path(root, RECOVERY_PATH)

    if not dry_run:
        write_text_utf8_atomic(current_path, current_text)
        write_text_utf8_atomic(index_path, index_text)
        write_text_utf8_atomic(recovery_path, recovery_text)

    return IndexWriteResult(
        paths=(current_path, index_path, recovery_path),
        dry_run=dry_run,
        current_text=current_text,
        index_text=index_text,
        recovery_text=recovery_text,
        conflicts=snapshot.conflicts,
    )


def check_generated_views(workspace_root: str | Path) -> IndexCheckResult:
    root = Path(workspace_root).expanduser().resolve()
    expected = generate_index_views(root, dry_run=True)
    messages: list[str] = []
    for relative_path, expected_text in (
        (CURRENT_PATH, expected.current_text),
        (INDEX_PATH, expected.index_text),
        (RECOVERY_PATH, expected.recovery_text),
    ):
        path = resolve_workspace_path(root, relative_path)
        if not path.exists():
            messages.append(f"missing: {relative_path}")
            continue
        if read_text_utf8(path) != expected_text:
            messages.append(f"stale: {relative_path}")

    messages.extend(f"conflict: {item}" for item in expected.conflicts)
    if expected.conflicts:
        status = "conflict"
    elif messages:
        status = "stale"
    else:
        status = "clean"
    return IndexCheckResult(
        clean=not messages,
        status=status,
        messages=messages,
        conflicts=expected.conflicts,
    )


def _collect_snapshot(root: Path) -> _IndexSnapshot:
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
            records.append(_YamlRecord(kind=kind, path=path, relative_path=relative_path, data=None, error="invalid_yaml"))
            continue
        if data is None:
            continue
        if not isinstance(data, dict):
            records.append(_YamlRecord(kind=kind, path=path, relative_path=relative_path, data=None, error="invalid_yaml"))
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
            task_requirement_id = str(task.data.get("requirement_id", "")).strip() if task.data else ""
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


def _record_link(record: _YamlRecord) -> str:
    label = _markdown_link_label(record.title or record.id or record.relative_path)
    return f"[{label}]({record.relative_path})"


def _requirement_link(requirement_by_id: dict[str, _YamlRecord], requirement_id: str) -> str:
    requirement = requirement_by_id.get(requirement_id)
    if requirement is not None:
        return _record_link(requirement)
    if not requirement_id or requirement_id == "-":
        return "-"
    return f"(missing requirement: `{requirement_id}`)"


def _markdown_link_label(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]").strip() or "-"


def _render_current(snapshot: _IndexSnapshot) -> str:
    active_tasks = [
        task
        for task in snapshot.tasks
        if str(task.data.get("stage", "") if task.data else "") not in {"done", "obsolete"}
    ]
    active_tasks = sorted(
        active_tasks,
        key=lambda item: (
            _record_timestamp(item, "updated_at"),
            _record_timestamp(item, "created_at"),
            item.id,
        ),
        reverse=True,
    )
    actionable_tasks = [task for task in active_tasks if not _is_waiting_feedback_task(task)]
    waiting_feedback_tasks = [task for task in active_tasks if _is_waiting_feedback_task(task)]
    workspace_state = "baseline" if not snapshot.requirements and not active_tasks else "active"
    active_task_count = "none" if not active_tasks else str(len(active_tasks))
    recommended_entry = "chat_or_explore" if not active_tasks else "resume_or_task"
    write_state = "no_by_default" if not active_tasks else "cli_only"
    requirement_by_id = {record.id: record for record in snapshot.requirements}
    lines = [
        "# CURRENT",
        "",
        "> 生成的最近工作面板；详细状态以任务包和命令输出为准。",
        "",
        "## 入口建议",
        "",
        "| 字段 | 值 |",
        "|---|---|",
        f"| workspace_state | {workspace_state} |",
        f"| active_tasks | {active_task_count} |",
        f"| recommended_entry | {recommended_entry} |",
        f"| write_state | {write_state} |",
        "",
        "## 最近可推进",
        "",
    ]
    lines.extend(
        _current_task_table_lines(
            actionable_tasks[:CURRENT_TASK_LIMIT],
            requirement_by_id,
            empty_message="no actionable tasks",
        )
    )
    remaining_actionable = len(actionable_tasks) - CURRENT_TASK_LIMIT
    if remaining_actionable > 0:
        lines.extend(["", f"> 还有 {remaining_actionable} 个可推进任务未展示；查 `docs/generated/index.md`。"])
    lines.extend(["", "## 等待反馈", ""])
    lines.extend(
        _current_task_table_lines(
            waiting_feedback_tasks[:CURRENT_WAITING_FEEDBACK_LIMIT],
            requirement_by_id,
            empty_message="no waiting feedback",
        )
    )
    remaining_waiting = len(waiting_feedback_tasks) - CURRENT_WAITING_FEEDBACK_LIMIT
    if remaining_waiting > 0:
        lines.extend(["", f"> 还有 {remaining_waiting} 个等待反馈任务未展示；查 `docs/generated/index.md`。"])
    lines.extend(
        [
            "",
            "## 读取边界",
            "",
            "- 本文件只展示最近工作面板，不是真源，也不作为单任务锁。",
            "- 任务事实以 `docs/active/*/task.yaml` 为准。",
            "- 查完整 active 目录看 `docs/generated/index.md`；续接和异常看 `docs/generated/recovery.md`。",
            "- 服务实时状态、开工 guard 和可执行边界以 `task context` / `service context` 为准。",
        ]
    )
    return _final_newline(lines)


def _current_task_table_lines(
    tasks: list[_YamlRecord],
    requirement_by_id: dict[str, _YamlRecord],
    *,
    empty_message: str,
) -> list[str]:
    lines = [
        "| 需求 | 任务 | 阶段 | 服务 refs | 风险缺口 | 验证 | 下一步 | 最近更新 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not tasks:
        lines.append(f"| - | - | - | - | - | - | {empty_message} | - |")
        return lines
    for task in tasks:
        data = task.data or {}
        requirement_id = str(data.get("requirement_id", "")).strip() or "-"
        updated_at = _record_timestamp(task, "updated_at") or "-"
        stage = str(data.get("stage", "unknown")).strip() or "unknown"
        validation = data.get("validation", {})
        validation_status = "not_started"
        if isinstance(validation, dict):
            validation_status = str(validation.get("status", "not_started")).strip() or "not_started"
        next_step = str(data.get("next_step", "")).strip() or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(_requirement_link(requirement_by_id, requirement_id)),
                    _table_cell(_record_link(task)),
                    _table_cell(stage),
                    _table_cell(_task_service_refs(task)),
                    _table_cell(_task_risk_gaps(task)),
                    _table_cell(validation_status),
                    _table_cell(next_step),
                    _table_cell(updated_at),
                ]
            )
            + " |"
        )
    return lines


def _is_waiting_feedback_task(task: _YamlRecord) -> bool:
    data = task.data or {}
    stage = str(data.get("stage", "")).strip()
    handoff = data.get("handoff", {})
    handoff_status = ""
    if isinstance(handoff, dict):
        handoff_status = str(handoff.get("status", "")).strip()
    return stage == "verification_pending" or handoff_status == "waiting_user_validation"


def _render_index(snapshot: _IndexSnapshot) -> str:
    lines = [
        "# Active Index",
        "",
        "> generated view; YAML remains the source of truth.",
        "",
        "## Requirements",
        "",
    ]
    lines.extend(_requirement_lines(snapshot.requirements, snapshot.tasks))
    lines.extend(["", "## Tasks", ""])
    lines.extend(_task_lines(snapshot.tasks, snapshot.requirements))
    lines.extend(["", "## Services", ""])
    lines.extend(_service_lines(snapshot.services))
    lines.extend(["", "## Materials", ""])
    lines.extend(_material_lines(snapshot.materials))
    lines.extend(["", "## Discovery", ""])
    lines.extend(_record_lines(snapshot.discoveries, include_title=True))
    lines.extend(["", "## Evidence", ""])
    lines.extend(_evidence_lines(snapshot.evidences))
    lines.extend(["", "## Archive", ""])
    lines.extend(_archive_lines(snapshot.archives))
    lines.extend(["", "## Actions", ""])
    lines.extend(_record_lines(snapshot.actions, include_title=True))
    lines.extend(["", "## Changes", ""])
    lines.extend(_record_lines(snapshot.changes, include_title=True))
    lines.extend(["", "## Decisions", ""])
    lines.extend(_record_lines(snapshot.decisions, include_title=True))
    lines.extend(["", "## Suspicions", ""])
    lines.extend(_record_lines(snapshot.suspicions, include_title=True))
    lines.extend(["", "## Conflict Report", ""])
    lines.extend(_conflict_lines(snapshot.conflicts))
    return _final_newline(lines)


def _render_recovery(snapshot: _IndexSnapshot) -> str:
    lines = [
        "# Recovery",
        "",
        "> 生成的续接队列；真实工作现场以 task context、任务包和命令输出为准。",
        "",
        "## 可续接任务",
        "",
    ]
    active_tasks = [
        task
        for task in snapshot.tasks
        if str(task.data.get("stage", "") if task.data else "") not in {"done", "obsolete"}
    ]
    if active_tasks:
        active_tasks = sorted(
            active_tasks,
            key=lambda item: (
                _record_timestamp(item, "updated_at"),
                _record_timestamp(item, "created_at"),
                item.id,
            ),
            reverse=True,
        )
        requirement_by_id = {requirement.id: requirement for requirement in snapshot.requirements}
        for task in active_tasks[:RECOVERY_TASK_LIMIT]:
            lines.extend(_task_recovery_lines(task, requirement_by_id))
        remaining = len(active_tasks) - RECOVERY_TASK_LIMIT
        if remaining > 0:
            lines.append(f"- and {remaining} more active tasks")
    else:
        lines.append("- no active tasks")

    lines.extend(["", "## 阻塞或异常", ""])
    blocked_lines = _blocked_task_lines(active_tasks)
    if blocked_lines:
        lines.extend(blocked_lines)
    else:
        lines.append("- none")

    lines.extend(["", "## 冲突", ""])
    lines.extend(_limited_conflict_lines(snapshot.conflicts))
    return _final_newline(lines)


def _task_recovery_lines(task: _YamlRecord, requirement_by_id: dict[str, _YamlRecord]) -> list[str]:
    data = task.data or {}
    stage = str(data.get("stage", "unknown")).strip() or "unknown"
    requirement_id = str(data.get("requirement_id", "")).strip()
    next_step = str(data.get("next_step", "")).strip()
    blocked = data.get("blocked", {})
    blocked_reason = ""
    if isinstance(blocked, dict):
        blocked_reason = str(blocked.get("reason", "")).strip()
    validation = data.get("validation", {})
    validation_status = ""
    evidence_ref = ""
    if isinstance(validation, dict):
        validation_status = str(validation.get("status", "")).strip()
        evidence_ref = str(validation.get("evidence_ref", "")).strip()

    lines = [
        f"- {_record_link(task)} [{stage}]",
        f"  - 需求：{_requirement_link(requirement_by_id, requirement_id)}",
        f"  - 服务 refs：{_task_service_refs(task)}",
        f"  - 风险缺口：{_task_risk_gaps(task)}",
        f"  - 验证：{validation_status or 'not_started'}",
    ]
    if next_step:
        lines.append(f"  - 下一步：{next_step}")
    if blocked_reason:
        lines.append(f"  - 阻塞：{blocked_reason}")
    if evidence_ref:
        lines.append(f"  - evidence：`{evidence_ref}`")
    return lines


def _blocked_task_lines(tasks: list[_YamlRecord]) -> list[str]:
    lines: list[str] = []
    for task in tasks:
        data = task.data or {}
        blocked = data.get("blocked", {})
        reason = ""
        if isinstance(blocked, dict):
            reason = str(blocked.get("reason", "")).strip()
        if reason:
            lines.append(f"- {_record_link(task)}：{reason}")
        if len(lines) >= RECOVERY_TASK_LIMIT:
            break
    return lines


def _requirement_lines(records: list[_YamlRecord], tasks: list[_YamlRecord]) -> list[str]:
    if not records:
        return ["- none"]
    lines: list[str] = []
    lines.extend(
        [
            "| 需求 | readiness | 任务数 | 最近更新 |",
            "|---|---|---:|---|",
        ]
    )
    task_counts: dict[str, int] = {}
    for task in tasks:
        if not task.data:
            continue
        requirement_id = str(task.data.get("requirement_id", "")).strip()
        if requirement_id:
            task_counts[requirement_id] = task_counts.get(requirement_id, 0) + 1
    for record in sorted(records, key=lambda item: item.id):
        readiness = record.data.get("readiness", {}) if record.data else {}
        status = readiness.get("status", "unknown") if isinstance(readiness, dict) else "unknown"
        updated_at = _record_timestamp(record, "updated_at") or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(_record_link(record)),
                    _table_cell(str(status)),
                    str(task_counts.get(record.id, 0)),
                    _table_cell(updated_at),
                ]
            )
            + " |"
        )
    return lines


def _task_lines(records: list[_YamlRecord], requirements: list[_YamlRecord]) -> list[str]:
    if not records:
        return ["- none"]
    requirement_by_id = {record.id: record for record in requirements}
    lines: list[str] = []
    lines.extend(
        [
            "| 需求 | 任务 | 阶段 | 风险 | 影响面 | 缺口 | 包内容 | 验证 | 最近更新 | 下一步 |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for record in sorted(records, key=lambda item: item.id):
        data = record.data or {}
        requirement_id = str(data.get("requirement_id", "")).strip() or "-"
        stage = str(data.get("stage", "unknown")).strip() or "unknown"
        validation = data.get("validation", {})
        validation_status = "not_started"
        if isinstance(validation, dict):
            validation_status = str(validation.get("status", "not_started")).strip() or "not_started"
        updated_at = _record_timestamp(record, "updated_at") or "-"
        next_step = str(data.get("next_step", "")).strip() or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(_requirement_link(requirement_by_id, requirement_id)),
                    _table_cell(_record_link(record)),
                    _table_cell(stage),
                    _table_cell(_task_risk_summary(record)),
                    _table_cell(_task_impact_summary(record)),
                    _table_cell(_task_risk_gaps(record)),
                    _table_cell(_task_packet_status(record)),
                    _table_cell(validation_status),
                    _table_cell(updated_at),
                    _table_cell(next_step),
                ]
            )
            + " |"
        )
    return lines


def _service_lines(services: list[dict[str, Any]]) -> list[str]:
    if not services:
        return ["- none"]
    lines: list[str] = []
    for service in sorted(services, key=lambda item: str(item.get("name", ""))):
        name = str(service.get("name", "")).strip()
        purpose = str(service.get("purpose", "")).strip()
        suffix = f" - {purpose}" if purpose else ""
        lines.append(f"- `{name}`{suffix}")
    return lines


def _material_lines(materials: list[dict[str, Any]]) -> list[str]:
    if not materials:
        return ["- none"]
    lines: list[str] = []
    for material in sorted(materials, key=lambda item: str(item.get("id", ""))):
        material_id = str(material.get("id", "")).strip()
        title = str(material.get("title", "")).strip()
        summary = _safe_text(str(material.get("summary", "")).strip())
        suffix = f" - {summary}" if summary else ""
        lines.append(f"- `{material_id}` {title}{suffix}")
    return lines


def _evidence_lines(records: list[_YamlRecord]) -> list[str]:
    if not records:
        return ["- none"]
    lines: list[str] = []
    for record in sorted(records, key=lambda item: item.id):
        task_id = record.data.get("task_id", "unknown") if record.data else "unknown"
        conclusion = record.data.get("conclusion", "unknown") if record.data else "unknown"
        lines.append(f"- `{record.id}` task={task_id} conclusion={conclusion}")
    return lines


def _archive_lines(records: list[_YamlRecord]) -> list[str]:
    if not records:
        return ["- none"]
    lines: list[str] = []
    for record in sorted(records, key=lambda item: str(item.data.get("version", "")) if item.data else ""):
        if not record.data:
            continue
        try:
            ArchiveManifestState.model_validate(record.data)
        except ValidationError:
            continue
        version = str(record.data.get("version", record.path.parent.name)).strip()
        archived_at = str(record.data.get("archived_at", "unknown")).strip()
        requirement_ids = _string_list(record.data.get("requirement_ids", []))
        entries = record.data.get("entries", [])
        entry_ids = []
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("source_id"):
                    entry_ids.append(str(entry["source_id"]).strip())
        requirement_text = ", ".join(requirement_ids) if requirement_ids else "none"
        entry_text = ", ".join(entry_ids) if entry_ids else "none"
        lines.append(
            f"- `{version}` archived_at={archived_at} requirements={requirement_text} entries={entry_text}"
        )
    return lines


def _record_lines(records: list[_YamlRecord], *, include_title: bool) -> list[str]:
    if not records:
        return ["- none"]
    lines: list[str] = []
    for record in sorted(records, key=lambda item: item.id):
        title = f" {record.title}" if include_title and record.title else ""
        lines.append(f"- `{record.id}`{title}")
    return lines


def _record_timestamp(record: _YamlRecord, field_name: str) -> str:
    if not record.data:
        return ""
    value = record.data.get(field_name, "")
    return str(value).strip() if value is not None else ""


def _task_packet_status(task: _YamlRecord) -> str:
    status_parts: list[str] = []
    if _has_nonempty_file(task.path.parent / "review.md"):
        status_parts.append("review")
    if _has_nonempty_file(task.path.parent / "implementation.md"):
        status_parts.append("implementation")
    if _has_nonempty_file(task.path.parent / "evidence.md") or (task.path.parent / "evidence.yaml").exists():
        status_parts.append("evidence")
    if _has_nonempty_file(task.path.parent / "handoff.md"):
        status_parts.append("handoff")
    return ", ".join(status_parts) if status_parts else "-"


def _task_risk_summary(task: _YamlRecord) -> str:
    model = _task_model_or_none(task)
    if model is not None:
        return risk_level_summary(model)
    data = task.data or {}
    risk_level = str(data.get("risk_level", "low")).strip() or "low"
    process_level = str(data.get("process_level", "micro")).strip() or "micro"
    return f"{risk_level}/{process_level}"


def _task_impact_summary(task: _YamlRecord) -> str:
    model = _task_model_or_none(task)
    if model is None:
        return "invalid"
    return impact_summary(model)


def _task_risk_gaps(task: _YamlRecord) -> str:
    model = _task_model_or_none(task)
    if model is None:
        return "invalid_task_model"
    return risk_gap_summary(model)


def _task_service_refs(task: _YamlRecord) -> str:
    data = task.data or {}
    services = _string_list(data.get("service_refs", []))
    if not services:
        return "-"
    return ", ".join(f"`{service}`" for service in services)


def _task_model_or_none(task: _YamlRecord) -> TaskState | None:
    if not task.data:
        return None
    try:
        return TaskState.model_validate(task.data)
    except ValidationError:
        return None


def _has_nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and bool(read_text_utf8(path).strip())
    except OSError:
        return False


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip() or "-"


def _conflict_lines(conflicts: list[str]) -> list[str]:
    if not conflicts:
        return ["- none"]
    return [f"- {item}" for item in sorted(conflicts)]


def _limited_conflict_lines(conflicts: list[str]) -> list[str]:
    if not conflicts:
        return ["- none"]
    sorted_conflicts = sorted(conflicts)
    lines = [f"- {item}" for item in sorted_conflicts[:RECOVERY_CONFLICT_LIMIT]]
    remaining = len(sorted_conflicts) - RECOVERY_CONFLICT_LIMIT
    if remaining > 0:
        lines.append(f"- and {remaining} more conflicts")
    return lines


def _safe_text(value: str) -> str:
    lowered = value.lower()
    if any(marker in lowered for marker in REDACT_MARKERS):
        return "[redacted]"
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _final_newline(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"
