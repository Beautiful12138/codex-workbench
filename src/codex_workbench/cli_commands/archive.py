from __future__ import annotations

from pathlib import Path

import typer

from ..archive import archive_version, list_archive_versions, plan_version_archive
from ..errors import WorkbenchError
from ..workspace import find_workspace_root
from .common import (
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

archive_app = typer.Typer(help="版本归档工具。", no_args_is_help=True)

@archive_app.callback()
def archive_callback() -> None:
    """archive 命令组。"""

@archive_app.command("preflight")
def archive_preflight(
    version: str = typer.Argument(..., help="归档版本号。"),
    requirement_id: list[str] = typer.Option([], "--requirement-id", help="要归档的 requirement，可重复。"),
    authorization_note: str = typer.Option("", "--authorization-note", help="用户归档授权说明。"),
    archived_at: str = typer.Option(..., "--archived-at", help="归档时间。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """只做版本归档预检，不写入文件。"""
    try:
        root = find_workspace_root(workspace_root)
        plan = plan_version_archive(
            root,
            version=version,
            requirement_ids=requirement_id,
            archive_authorization_note=authorization_note,
            archived_at=archived_at,
        )
        typer.echo("archive preflight clean")
        for warning in sorted(dict.fromkeys(plan.doctor_warnings)):
            typer.echo(f"warning {warning}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@archive_app.command("version")
def archive_version_command(
    version: str = typer.Argument(..., help="归档版本号。"),
    requirement_id: list[str] = typer.Option([], "--requirement-id", help="要归档的 requirement，可重复。"),
    authorization_note: str = typer.Option("", "--authorization-note", help="用户归档授权说明。"),
    archived_at: str = typer.Option(..., "--archived-at", help="归档时间。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将移动或写入的路径。"),
) -> None:
    """按版本归档已关闭 requirement 及其任务包。"""
    try:
        root = find_workspace_root(workspace_root)
        result = archive_version(
            root,
            version=version,
            requirement_ids=requirement_id,
            archive_authorization_note=authorization_note,
            archived_at=archived_at,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="archived")
        _refresh_generated_views(root, dry_run=dry_run)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@archive_app.command("list")
def archive_list(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """按需列出版本归档历史。"""
    try:
        root = find_workspace_root(workspace_root)
        summaries = list_archive_versions(root)
        if not summaries:
            typer.echo("archive empty")
            return
        for summary in summaries:
            requirements = ", ".join(summary.requirement_ids) if summary.requirement_ids else "none"
            typer.echo(
                f"`{summary.version}` archived_at={summary.archived_at} requirements={requirements}"
            )
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)
