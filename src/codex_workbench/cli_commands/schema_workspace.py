from __future__ import annotations

from pathlib import Path

import typer

from ..advice import workspace_advice_lines
from .._index_records import collect_snapshot
from .._index_types import _IndexSnapshot, _YamlRecord
from .._index_views import _final_newline, _record_timestamp, _task_risk_gaps
from ..errors import ErrorCode, WorkbenchError
from ..schema import core_model_json_schemas
from ..task_context import build_task_context
from ..workspace import find_workspace_root
from .common import _exit_with_workbench_error
from .requirement_task import _format_task_context
from .services import _format_service_context, service_context

schema_app = typer.Typer(help="schema 工具。", no_args_is_help=True)
workspace_app = typer.Typer(help="工作区工具。", no_args_is_help=True)

@schema_app.callback()
def schema_callback() -> None:
    """schema 命令组。"""

@workspace_app.callback()
def workspace_callback() -> None:
    """工作区命令组。"""

@schema_app.command("list")
def schema_list() -> None:
    """列出核心模型 schema。"""
    for model_name in sorted(core_model_json_schemas()):
        typer.echo(model_name)

@workspace_app.command("root")
def workspace_root(
    start: Path = typer.Option(
        Path("."),
        "--start",
        help="从指定路径向上查找工作区根目录。",
    ),
) -> None:
    """查找工作区根目录。"""
    try:
        typer.echo(str(find_workspace_root(start)))
    except WorkbenchError as exc:
        typer.echo(f"{exc.code.value}: {exc.message}", err=True)
        raise typer.Exit(exc.exit_code) from exc

@workspace_app.command("context")
def workspace_context_command(
    task_ref: str | None = typer.Option(None, "--task", help="可选：嵌入指定任务的 task context。"),
    service_name: str | None = typer.Option(None, "--service", help="可选：嵌入指定服务的 service context。"),
    project_name: str | None = typer.Option(None, "--project", help="只展示指定项目分组。"),
    ungrouped: bool = typer.Option(False, "--ungrouped", help="只展示未分组服务。"),
    check_services: bool = typer.Option(
        False,
        "--check-services",
        help="深入检查服务概览中展示的服务路径、Git、入口候选；默认只读 registry，避免大仓库变慢。",
    ),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """输出按需工作区驾驶舱，不生成或修改视图文件。"""
    try:
        if project_name is not None and ungrouped:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                "workspace_project_options_conflict",
                exit_code=2,
            )
        root = find_workspace_root(workspace_root)
        snapshot = collect_snapshot(root)
        lines = _workspace_context_lines(
            root,
            snapshot,
            project_name=project_name,
            ungrouped=ungrouped,
            check_services=check_services,
        )
        if task_ref:
            lines.extend(["", "## 当前任务", ""])
            lines.extend(_format_task_context(build_task_context(root, task_ref)).splitlines())
        if service_name:
            lines.extend(["", "## 当前服务", ""])
            lines.extend(_format_service_context(service_context(root, service_name)).splitlines())
        typer.echo(_final_newline(lines), nl=False)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


def _workspace_context_lines(
    root: Path,
    snapshot: _IndexSnapshot,
    *,
    project_name: str | None = None,
    ungrouped: bool = False,
    check_services: bool = False,
) -> list[str]:
    active_tasks = _active_tasks(snapshot)
    service_records = _registered_service_records(snapshot)
    selected_service_records = _select_service_records(
        service_records,
        project_name=project_name,
        ungrouped=ungrouped,
    )
    workspace_state = "baseline" if not snapshot.requirements and not active_tasks else "active"
    active_task_count = "none" if not active_tasks else str(len(active_tasks))
    recommended_entry = "chat_or_explore" if not active_tasks else "resume_or_task"
    lines = [
        "# Workspace Context",
        "",
        "> 按需驾驶舱，不生成文件；需要刷新视图时再运行 index generate。",
        "> 不是状态真源；任务事实以 task context、任务包和命令输出为准。",
        "",
        f"工作区状态：{workspace_state}",
        f"活动需求：{len(snapshot.requirements)}",
        f"活动任务：{active_task_count}",
        f"登记项目：{_registered_project_count(service_records)}",
        f"登记服务：{len(snapshot.services)}",
        f"推荐入口：{recommended_entry}",
        "状态写入：默认不写；需要写状态时必须有明确场景和授权，并且只能走 CLI",
        "",
        "默认路径：workspace context -> task context -> service context -> task package",
        "",
    ]
    service_ref_counts = _service_ref_counts(active_tasks)
    registered_names = {str(service.get("name", "")).strip() for service in service_records}
    unknown_refs = [name for name in service_ref_counts if name not in registered_names]
    lines.extend(
        _workspace_service_overview_lines(
            selected_service_records,
            unknown_refs,
            service_ref_counts,
        )
    )
    if check_services:
        lines.extend([""])
        lines.extend(
            _workspace_service_check_lines(
                root,
                selected_service_records,
                service_ref_counts,
            )
        )
    lines.extend(["", "## 任务焦点", ""])
    lines.extend(_workspace_task_focus_lines(active_tasks))

    lines.extend(["", "## 下一步建议", ""])
    lines.extend(
        f"- {line}"
        for line in workspace_advice_lines(
            active_requirement_count=len(snapshot.requirements),
            active_task_count=len(active_tasks),
            has_conflicts=bool(snapshot.conflicts),
            has_waiting_feedback=bool(_waiting_feedback_tasks(active_tasks)),
            has_blocked=bool(_blocked_tasks(active_tasks)),
            has_needs_confirmation=bool(_needs_confirmation_tasks(active_tasks)),
        )
    )

    lines.extend(["", "## 冲突", ""])
    conflict_lines = [f"- {item}" for item in snapshot.conflicts[:5]]
    lines.extend(conflict_lines if conflict_lines else ["- none"])
    remaining_conflicts = len(snapshot.conflicts) - 5
    if remaining_conflicts > 0:
        lines.append(f"- and {remaining_conflicts} more conflicts")
    return lines


def _workspace_service_overview_lines(
    service_records: list[dict[str, object]],
    unknown_refs: list[str],
    service_ref_counts: dict[str, int],
) -> list[str]:
    lines = [
        "## 项目与服务概览",
        "",
        "> 默认只读 `services/registry.yaml` 并全量展示服务名称；服务详情用 `--service` 点名查看。",
    ]
    if not service_records and not unknown_refs:
        lines.append("- none")
        return lines
    for project, project_services in _project_service_groups(service_records):
        label = project or "未分组"
        lines.append(f"- {label}：{len(project_services)} 个服务")
        for service in project_services:
            lines.append(f"  - {str(service.get('name', '')).strip()}")
    if unknown_refs:
        lines.extend(["", "### 未登记服务引用", ""])
        for name in unknown_refs[:5]:
            lines.append(
                f"- {name}：任务引用：{service_ref_counts[name]} | 阻断：unknown_service_ref"
            )
        remaining = len(unknown_refs) - 5
        if remaining > 0:
            lines.append(f"- and {remaining} more unknown service refs")
    return lines


def _workspace_service_check_lines(
    root: Path,
    service_records: list[dict[str, object]],
    service_ref_counts: dict[str, int],
) -> list[str]:
    lines = ["## 服务检查", ""]
    ordered_records = _ordered_service_records(service_records, service_ref_counts)
    if not ordered_records:
        lines.append("- none")
        return lines
    for service in ordered_records[:5]:
        name = str(service.get("name", "")).strip()
        try:
            context = service_context(root, name)
        except WorkbenchError as exc:
            lines.append(f"- {name}：unavailable | 阻断：{exc.code.value}")
            continue
        parts = [
            f"{context.path_state}",
            f"Git：{context.git_state}",
            f"入口：{_format_csv(context.entry_candidates)}",
        ]
        parts.append(f"任务引用：{service_ref_counts.get(name, 0)}")
        if context.hard_gaps:
            parts.append(f"阻断：{_format_csv(context.hard_gaps)}")
        if context.warnings:
            parts.append(f"提醒：{_format_csv(context.warnings)}")
        if context.dirty_count or context.untracked_count:
            parts.append(f"变更：dirty={context.dirty_count} untracked={context.untracked_count}")
        lines.append(f"- {name}：" + " | ".join(parts))
    remaining = len(ordered_records) - 5
    if remaining > 0:
        lines.append(f"- and {remaining} more unchecked services")
    return lines


def _registered_service_records(snapshot: _IndexSnapshot) -> list[dict[str, object]]:
    return [service for service in snapshot.services if str(service.get("name", "")).strip()]


def _registered_project_count(service_records: list[dict[str, object]]) -> int:
    return len({_service_project(service) for service in service_records} - {None})


def _select_service_records(
    service_records: list[dict[str, object]],
    *,
    project_name: str | None,
    ungrouped: bool,
) -> list[dict[str, object]]:
    if project_name is not None:
        available_projects = {_service_project(service) for service in service_records}
        if project_name not in available_projects:
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"unknown_project: {project_name}",
                exit_code=2,
            )
        return [service for service in service_records if _service_project(service) == project_name]
    if ungrouped:
        return [service for service in service_records if _service_project(service) is None]
    return service_records


def _project_service_groups(
    service_records: list[dict[str, object]],
) -> list[tuple[str | None, list[dict[str, object]]]]:
    groups: dict[str | None, list[dict[str, object]]] = {}
    for service in service_records:
        groups.setdefault(_service_project(service), []).append(service)
    return list(groups.items())


def _service_project(service: dict[str, object]) -> str | None:
    project = str(service.get("project", "")).strip()
    return project or None


def _ordered_service_records(
    service_records: list[dict[str, object]],
    service_ref_counts: dict[str, int],
) -> list[dict[str, object]]:
    indexed = list(enumerate(service_records))
    return [
        service
        for _, service in sorted(
            indexed,
            key=lambda pair: (
                0 if service_ref_counts.get(str(pair[1].get("name", "")).strip(), 0) else 1,
                -service_ref_counts.get(str(pair[1].get("name", "")).strip(), 0),
                pair[0],
            ),
        )
    ]


def _service_ref_counts(tasks: list[_YamlRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        seen: set[str] = set()
        data = task.data or {}
        raw_refs = data.get("service_refs", [])
        if not isinstance(raw_refs, list):
            continue
        for raw_ref in raw_refs:
            service_ref = str(raw_ref).strip()
            if not service_ref or service_ref in seen:
                continue
            counts[service_ref] = counts.get(service_ref, 0) + 1
            seen.add(service_ref)
    return counts


def _workspace_task_focus_lines(tasks: list[_YamlRecord]) -> list[str]:
    groups = (
        ("可续接", _resumable_tasks(tasks)),
        ("等待反馈", _waiting_feedback_tasks(tasks)),
        ("阻塞", _blocked_tasks(tasks)),
        ("需确认", _needs_confirmation_tasks(tasks)),
    )
    lines: list[str] = []
    for label, group_tasks in groups:
        lines.append(f"{label}：")
        if group_tasks:
            lines.extend(_workspace_focus_task_lines(group_tasks))
        else:
            lines.append("- none")
    return lines


def _workspace_focus_task_lines(tasks: list[_YamlRecord]) -> list[str]:
    lines = [_workspace_focus_task_line(task) for task in tasks[:5]]
    remaining = len(tasks) - 5
    if remaining > 0:
        lines.append(f"- and {remaining} more tasks")
    return lines


def _resumable_tasks(tasks: list[_YamlRecord]) -> list[_YamlRecord]:
    return [
        task
        for task in tasks
        if not _is_waiting_feedback(task)
        and not _is_blocked(task)
        and not _needs_confirmation(task)
    ]


def _waiting_feedback_tasks(tasks: list[_YamlRecord]) -> list[_YamlRecord]:
    return [task for task in tasks if _is_waiting_feedback(task) and not _is_blocked(task)]


def _blocked_tasks(tasks: list[_YamlRecord]) -> list[_YamlRecord]:
    return [task for task in tasks if _is_blocked(task)]


def _needs_confirmation_tasks(tasks: list[_YamlRecord]) -> list[_YamlRecord]:
    return [
        task
        for task in tasks
        if _needs_confirmation(task)
        and not _is_waiting_feedback(task)
        and not _is_blocked(task)
    ]


def _active_tasks(snapshot: _IndexSnapshot) -> list[_YamlRecord]:
    active_tasks = [
        task
        for task in snapshot.tasks
        if str(task.data.get("stage", "") if task.data else "") not in {"done", "obsolete"}
    ]
    return sorted(
        active_tasks,
        key=lambda item: (
            _record_timestamp(item, "updated_at"),
            _record_timestamp(item, "created_at"),
            item.id,
        ),
        reverse=True,
    )


def _workspace_focus_task_line(task: _YamlRecord) -> str:
    data = task.data or {}
    title = str(data.get("title", "")).strip() or task.title or "untitled task"
    stage = str(data.get("stage", "unknown")).strip() or "unknown"
    reason = _focus_reason(task)
    return f"- {title} [{stage}]：{reason}"


def _focus_reason(task: _YamlRecord) -> str:
    data = task.data or {}
    if _is_blocked(task):
        blocked = data.get("blocked", {})
        if isinstance(blocked, dict):
            reason = str(blocked.get("reason", "")).strip()
            if reason:
                return reason
    if _needs_confirmation(task):
        risk_gaps = _task_risk_gaps(task)
        if risk_gaps != "none":
            return risk_gaps
        risk_level = str(data.get("risk_level", "")).strip()
        process_level = str(data.get("process_level", "")).strip()
        if risk_level or process_level:
            return f"risk={risk_level or '-'} process={process_level or '-'}"
    return str(data.get("next_step", "")).strip() or "-"


def _is_waiting_feedback(task: _YamlRecord) -> bool:
    data = task.data or {}
    stage = str(data.get("stage", "")).strip()
    handoff = data.get("handoff", {})
    handoff_status = ""
    if isinstance(handoff, dict):
        handoff_status = str(handoff.get("status", "")).strip()
    return stage == "verification_pending" or handoff_status == "waiting_user_validation"


def _is_blocked(task: _YamlRecord) -> bool:
    data = task.data or {}
    stage = str(data.get("stage", "")).strip()
    blocked = data.get("blocked", {})
    if stage == "blocked":
        return True
    if isinstance(blocked, dict):
        return bool(str(blocked.get("reason", "")).strip())
    return False


def _needs_confirmation(task: _YamlRecord) -> bool:
    data = task.data or {}
    risk_level = str(data.get("risk_level", "")).strip()
    process_level = str(data.get("process_level", "")).strip()
    if risk_level in {"high", "critical"} or process_level in {"high", "critical"}:
        return True
    return _task_risk_gaps(task) != "none"


def _format_csv(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
