from __future__ import annotations

from pathlib import Path

import typer

from ..doctor import run_doctor
from ..errors import WorkbenchError
from ..index import check_generated_views, generate_index_views
from ..workspace import find_workspace_root
from .common import (
    _echo_index_check,
    _echo_index_conflicts,
    _echo_package_result,
    _exit_with_workbench_error,
    _format_doctor_finding,
)

index_app = typer.Typer(help="生成 CURRENT、索引和恢复视图工具。", no_args_is_help=True)
doctor_app = typer.Typer(help="工作区健康检查工具。", no_args_is_help=True)

@index_app.callback()
def index_callback() -> None:
    """index 命令组。"""

@doctor_app.callback()
def doctor_callback() -> None:
    """doctor 命令组。"""

@index_app.command("generate")
def index_generate(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    check: bool = typer.Option(False, "--check", help="只检查 generated view 是否最新。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件和生成摘要。"),
) -> None:
    """生成 CURRENT、index 和 recovery 视图。"""
    try:
        root = find_workspace_root(workspace_root)
        if check:
            _echo_index_check(check_generated_views(root))
            return
        result = generate_index_views(root, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="generated")
        _echo_index_conflicts(result.conflicts)
        if dry_run:
            typer.echo(result.index_text.rstrip())
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@index_app.command("check")
def index_check(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """检查 generated view 是否与真源一致。"""
    try:
        root = find_workspace_root(workspace_root)
        _echo_index_check(check_generated_views(root))
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@doctor_app.command("check")
def doctor_check(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    show_warnings: bool = typer.Option(False, "--show-warnings", help="展开 warning 详情。"),
    show_suggestions: bool = typer.Option(False, "--show-suggestions", help="展开 suggestion 详情。"),
) -> None:
    """极简健康检查：默认只展开 Blocking。"""
    try:
        root = find_workspace_root(workspace_root)
        report = run_doctor(root)
        if report.blockings:
            for finding in report.blockings:
                typer.echo(_format_doctor_finding(finding), err=True)
            raise typer.Exit(1)
        typer.echo("doctor clean")
        if show_warnings:
            for finding in report.warnings:
                typer.echo(_format_doctor_finding(finding))
        if show_suggestions:
            for finding in report.suggestions:
                typer.echo(_format_doctor_finding(finding))
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)
