from __future__ import annotations

import json
from pathlib import Path

import typer

from ..errors import WorkbenchError
from ..services import (
    ServiceContext,
    add_service,
    delete_service,
    read_service_registry,
    service_context,
    service_status,
    update_service,
)
from ..workspace import find_workspace_root
from .common import (
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

service_app = typer.Typer(help="服务登记和只读状态工具。", no_args_is_help=True)

@service_app.callback()
def service_callback() -> None:
    """service 命令组。"""

@service_app.command("add")
def service_add(
    name: str = typer.Argument(..., help="服务名，例如 api。"),
    local_path: Path = typer.Option(..., "--path", help="服务本地路径。"),
    project: str | None = typer.Option(None, "--project", help="所属项目分组。"),
    purpose: str | None = typer.Option(None, "--purpose", help="服务用途说明。"),
    notes: str | None = typer.Option(None, "--notes", help="备注。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """登记服务。"""
    try:
        root = find_workspace_root(workspace_root)
        result = add_service(
            root,
            name=name,
            local_path=local_path,
            project=project,
            purpose=purpose,
            notes=notes,
            dry_run=dry_run,
        )
        _echo_package_result(root, (result.path,), dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@service_app.command("list")
def service_list(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出服务。"""
    try:
        root = find_workspace_root(workspace_root)
        registry = read_service_registry(root)
        for entry in registry.services:
            typer.echo(f"service {entry.name} {entry.local_path or '<missing-path>'}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@service_app.command("update")
def service_update(
    name: str = typer.Argument(..., help="服务名。"),
    local_path: Path | None = typer.Option(None, "--path", help="新的服务本地路径。"),
    project: str | None = typer.Option(None, "--project", help="新的项目分组。"),
    clear_project: bool = typer.Option(False, "--clear-project", help="移除项目分组。"),
    purpose: str | None = typer.Option(None, "--purpose", help="新的服务用途说明。"),
    notes: str | None = typer.Option(None, "--notes", help="新的备注。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """更新服务登记。"""
    try:
        root = find_workspace_root(workspace_root)
        result = update_service(
            root,
            name=name,
            local_path=local_path,
            project=project,
            clear_project=clear_project,
            purpose=purpose,
            notes=notes,
            dry_run=dry_run,
        )
        _echo_package_result(root, (result.path,), dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@service_app.command("delete")
def service_delete(
    name: str = typer.Argument(..., help="服务名。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """删除服务登记。"""
    try:
        root = find_workspace_root(workspace_root)
        result = delete_service(root, name=name, dry_run=dry_run)
        _echo_package_result(root, (result.path,), dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@service_app.command("status")
def service_status_command(
    name: str = typer.Argument(..., help="服务名。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """输出服务路径和 Git 的只读状态摘要。"""
    try:
        root = find_workspace_root(workspace_root)
        status = service_status(root, name)
        line = f"{status.name} path={status.path or '<missing-path>'} exists={status.exists} git_state={status.git_state}"
        visible_files = f">={status.visible_file_count}" if status.visible_file_count_limit_reached else str(status.visible_file_count)
        line += f" path_state={status.path_state} visible_files={visible_files}"
        if status.branch:
            line += f" branch={status.branch}"
        if status.head:
            line += f" head={status.head}"
        if status.git_status_scope:
            line += f" git_scope={status.git_status_scope}"
        if status.service_relpath:
            line += f" service_relpath={status.service_relpath}"
        if status.git_error:
            line += f" git_error={status.git_error}"
        if status.git_state == "git":
            line += f" dirty={status.dirty_count} untracked={status.untracked_count}"
        typer.echo(line)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@service_app.command("context")
def service_context_command(
    name: str = typer.Argument(..., help="服务名。"),
    output_format: str = typer.Option("text", "--format", help="输出格式：text/json。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """输出服务是否可接任务的只读上下文。"""
    try:
        if output_format not in {"text", "json"}:
            typer.echo(f"validation_error: unsupported_format: {output_format}", err=True)
            raise typer.Exit(2)
        root = find_workspace_root(workspace_root)
        context = service_context(root, name)
        if output_format == "json":
            typer.echo(json.dumps(_service_context_payload(context), ensure_ascii=False, indent=2))
            return
        typer.echo(_format_service_context(context))
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


def _format_service_context(context: ServiceContext) -> str:
    path = context.resolved_path or "<missing-path>"
    visible_files = f">={context.visible_file_count}" if context.visible_file_count_limit_reached else str(context.visible_file_count)
    lines = [
        f"服务：{context.name}",
        f"项目：{context.project or '未分组'}",
    ]
    if context.purpose:
        lines.append(f"用途：{context.purpose}")
    if context.notes:
        lines.append(f"备注：{context.notes}")
    lines.extend(
        [
            f"路径：{path}",
            f"状态：{context.path_state} | Git：{context.git_state} | 可见文件：{visible_files}",
            f"入口候选：{_format_csv(context.entry_candidates)}",
        ]
    )
    if context.git_root and context.git_status_scope:
        lines.append(
            (
                "Git 范围："
                f"git_status={context.git_status_scope},service_relpath={context.service_relpath or '<unknown>'}"
            )
        )
    if context.branch or context.head:
        lines.append(f"Git 版本：branch={context.branch or '<unknown>'} head={context.head or '<unknown>'}")
    if context.git_error:
        lines.append(f"Git 错误：{context.git_error}")
    if context.hard_gaps:
        lines.append(f"阻断：{_format_csv(context.hard_gaps)}")
    if context.warnings:
        lines.append(f"提醒：{_format_csv(context.warnings)}")
    if context.dirty_count or context.untracked_count:
        lines.append(f"已有变更：dirty={context.dirty_count} untracked={context.untracked_count}")
    return "\n".join(lines)


def _service_context_payload(context: ServiceContext) -> dict[str, object]:
    return {
        "name": context.name,
        "project": context.project,
        "registry_state": context.registry_state,
        "raw_path": context.raw_path,
        "purpose": context.purpose,
        "notes": context.notes,
        "resolved_path": str(context.resolved_path) if context.resolved_path else None,
        "path_state": context.path_state,
        "visible_file_count": context.visible_file_count,
        "visible_file_count_limit_reached": context.visible_file_count_limit_reached,
        "git_state": context.git_state,
        "git_root": str(context.git_root) if context.git_root else None,
        "service_relpath": context.service_relpath,
        "git_status_scope": context.git_status_scope,
        "git_error": context.git_error,
        "branch": context.branch,
        "head": context.head,
        "dirty_count": context.dirty_count,
        "untracked_count": context.untracked_count,
        "entry_candidates": list(context.entry_candidates),
        "gaps": list(context.gaps),
        "hard_gaps": list(context.hard_gaps),
        "warnings": list(context.warnings),
    }


def _format_csv(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
