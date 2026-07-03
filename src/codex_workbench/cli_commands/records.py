from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from ..errors import WorkbenchError
from ..records import (
    classify_change,
    create_action_note,
    create_change_record,
    create_decision_record,
    create_suspicion_log,
)
from ..workspace import find_workspace_root
from .common import (
    _echo_markdown_template_hint,
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

action_app = typer.Typer(help="非任务动作记录工具。", no_args_is_help=True)
change_app = typer.Typer(help="正式范围变化记录工具。", no_args_is_help=True)
decision_app = typer.Typer(help="冷路径长期决策记录工具。", no_args_is_help=True)
suspicion_app = typer.Typer(help="疑点线索记录工具。", no_args_is_help=True)

@action_app.callback()
def action_callback() -> None:
    """action 命令组。"""

@change_app.callback()
def change_callback() -> None:
    """change 命令组。"""

@decision_app.callback()
def decision_callback() -> None:
    """decision 命令组。"""

@suspicion_app.callback()
def suspicion_callback() -> None:
    """suspicion 命令组。"""

@action_app.command("create")
def action_create(
    action_id: str = typer.Argument(..., help="动作记录 ID，例如 ACT-001。"),
    title: str = typer.Option(..., "--title", help="动作标题。"),
    summary: str = typer.Option(..., "--summary", help="动作摘要。"),
    action_type: str = typer.Option(
        "maintenance_action",
        "--action-type",
        help="动作分类：maintenance_action、ops_action 或 ephemeral_check。",
    ),
    status: str = typer.Option(
        "executed",
        "--status",
        help="动作状态：planned、executed、partial、failed 或 reverted。",
    ),
    authorization: str | None = typer.Option(None, "--authorization", help="授权说明，可选。"),
    target: str | None = typer.Option(None, "--target", help="动作目标，可选。"),
    result_note: str | None = typer.Option(None, "--result", help="动作结果，可选。"),
    related_ref: list[str] = typer.Option([], "--related-ref", help="关联需求、任务或材料，可重复。"),
    side_effect_summary: str = typer.Option(
        "no_side_effect",
        "--side-effect-summary",
        help="动作副作用摘要；没有副作用时使用 no_side_effect。",
    ),
    rollback_hint: str = typer.Option(
        "no_rollback_needed",
        "--rollback-hint",
        help="回滚提示；无需回滚时使用 no_rollback_needed。",
    ),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 action note；它不替代 evidence 或 validation。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_action_note(
            root,
            action_id=action_id,
            title=title,
            summary=summary,
            action_type=action_type,
            status=status,
            authorization=authorization,
            target=target,
            result=result_note,
            related_refs=related_ref,
            side_effect_summary=side_effect_summary,
            rollback_hint=rollback_hint,
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

@change_app.command("classify")
def change_classify(
    kind: str = typer.Option(
        ...,
        "--kind",
        help="变化分类：implementation_adjustment、scope_clarification 或 scope_change。",
    ),
    summary: str = typer.Option(..., "--summary", help="变化摘要。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """分类变化；implementation adjustment 不生成正式 change record。"""
    try:
        find_workspace_root(workspace_root)
        result = classify_change(kind=kind, summary=summary)
        typer.echo(
            f"{result.kind.value} requires_change_record={str(result.requires_change_record).lower()} reason={result.reason_code}"
        )
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@change_app.command("create")
def change_create(
    change_id: str = typer.Argument(..., help="变更记录 ID，例如 CHG-001。"),
    title: str = typer.Option(..., "--title", help="变更标题。"),
    changed_area: str = typer.Option(..., "--changed-area", help="变化区域。"),
    reason: str = typer.Option(..., "--reason", help="变化原因。"),
    impact: str = typer.Option(..., "--impact", help="影响说明。"),
    handling: str = typer.Option(..., "--handling", help="处理方式。"),
    related_ref: list[str] = typer.Option([], "--related-ref", help="关联需求、任务或材料，可重复。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 formal scope change 记录。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_change_record(
            root,
            change_id=change_id,
            title=title,
            changed_area=changed_area,
            reason=reason,
            impact=impact,
            handling=handling,
            related_refs=related_ref,
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

@decision_app.command("create")
def decision_create(
    decision_id: str = typer.Argument(..., help="决策记录 ID，例如 DEC-001。"),
    title: str = typer.Option(..., "--title", help="决策标题。"),
    cold_path_reason: str = typer.Option(..., "--cold-path-reason", help="冷路径原因。"),
    context: str = typer.Option(..., "--context", help="决策上下文。"),
    decision: str = typer.Option(..., "--decision", help="决策内容。"),
    impact: str = typer.Option(..., "--impact", help="影响说明。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建冷路径 Decision Record。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_decision_record(
            root,
            decision_id=decision_id,
            title=title,
            cold_path_reason=cold_path_reason,
            context=context,
            decision=decision,
            impact=impact,
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

@suspicion_app.command("create")
def suspicion_create(
    suspicion_id: str = typer.Argument(..., help="疑点记录 ID，例如 SUS-001。"),
    title: str = typer.Option(..., "--title", help="疑点标题。"),
    location_or_subject: str = typer.Option(..., "--location", help="位置或对象。"),
    fact: list[str] = typer.Option(..., "--fact", help="已确认事实，可重复。"),
    inference: list[str] = typer.Option(..., "--inference", help="AI 推断，可重复。"),
    assumption: list[str] = typer.Option([], "--assumption", help="未确认假设，可重复。"),
    current_task_impact: str = typer.Option(..., "--current-task-impact", help="当前任务影响。"),
    suggested_handling: str = typer.Option(..., "--suggested-handling", help="建议处理方式。"),
    related_ref: list[str] = typer.Option([], "--related-ref", help="关联需求、任务或材料，可重复。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 Suspicion Log；它只记录线索，不授权修改。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_suspicion_log(
            root,
            suspicion_id=suspicion_id,
            title=title,
            location_or_subject=location_or_subject,
            confirmed_facts=fact,
            ai_inferences=inference,
            assumptions=assumption,
            current_task_impact=current_task_impact,
            suggested_handling=suggested_handling,
            related_refs=related_ref,
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
