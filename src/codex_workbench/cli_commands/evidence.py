from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from ..errors import WorkbenchError
from ..validation import (
    apply_validation,
    create_evidence_record,
    set_handoff_status,
)
from ..workspace import find_workspace_root
from .common import (
    _echo_markdown_template_hint,
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

evidence_app = typer.Typer(help="验证证据工具。", no_args_is_help=True)
validation_app = typer.Typer(help="验证结论工具。", no_args_is_help=True)
handoff_app = typer.Typer(help="用户验收交接工具。", no_args_is_help=True)

@evidence_app.callback()
def evidence_callback() -> None:
    """evidence 命令组。"""

@validation_app.callback()
def validation_callback() -> None:
    """validation 命令组。"""

@handoff_app.callback()
def handoff_callback() -> None:
    """handoff 命令组。"""

@evidence_app.command("create")
def evidence_create(
    evidence_id: str = typer.Argument(..., help="证据 ID，例如 EV-REQ-20260702-001-TASK-20260702-001。"),
    task_id: str = typer.Option(..., "--task-id", help="关联任务 ID。"),
    conclusion: str = typer.Option(..., "--conclusion", help="证据结论。"),
    key_output: list[str] = typer.Option(
        ...,
        "--key-output",
        help="关键验证输出摘要，可重复。",
    ),
    unverified_item: list[str] = typer.Option(
        [],
        "--unverified-item",
        help="未验证项，可重复。",
    ),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 evidence 记录；只记录已经发生的验证事实。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_evidence_record(
            root,
            evidence_id=evidence_id,
            task_id=task_id,
            conclusion=conclusion,
            key_outputs=key_output,
            unverified_items=unverified_item,
            updated_at=updated_at,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run)
        _refresh_generated_views(root, dry_run=dry_run)
        _echo_markdown_template_hint()
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@validation_app.command("apply")
def validation_apply(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    evidence_id: str = typer.Option(..., "--evidence-id", help="要应用的 evidence ID。"),
    status: str = typer.Option(..., "--status", help="验证结论。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """将真实 evidence 判断写回 task.yaml 的 validation 维度。"""
    try:
        root = find_workspace_root(workspace_root)
        result = apply_validation(
            root,
            task_id=task_id,
            evidence_id=evidence_id,
            status=status,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@handoff_app.command("set")
def handoff_set(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    status: str = typer.Option(..., "--status", help="handoff 状态。"),
    note: str | None = typer.Option(None, "--note", help="交接说明。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """更新 handoff 维度，不替代 validation。"""
    try:
        root = find_workspace_root(workspace_root)
        result = set_handoff_status(
            root,
            task_id=task_id,
            status=status,
            note=note,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)
