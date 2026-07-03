from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from ..errors import WorkbenchError
from ..ids import allocate_requirement_id
from ..materials import (
    add_material,
    confirm_intake,
    create_discovery_package,
    create_intake_draft,
    read_material_registry,
)
from ..templates import RequirementTemplateContext, TemplateError
from ..timeutils import resolve_timestamp
from ..workspace import find_workspace_root
from .common import (
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

material_app = typer.Typer(help="材料登记工具。", no_args_is_help=True)
discovery_app = typer.Typer(help="发现记录工具。", no_args_is_help=True)
intake_app = typer.Typer(help="intake 草案和确认工具。", no_args_is_help=True)

@material_app.callback()
def material_callback() -> None:
    """material 命令组。"""

@discovery_app.callback()
def discovery_callback() -> None:
    """discovery 命令组。"""

@intake_app.callback()
def intake_callback() -> None:
    """intake 命令组。"""

@material_app.command("add")
def material_add(
    material_id: str = typer.Argument(..., help="材料 ID，例如 MAT-001。"),
    title: str = typer.Option(..., "--title", help="材料标题。"),
    source: str = typer.Option(..., "--source", help="材料来源。"),
    summary: str = typer.Option(..., "--summary", help="脱敏摘要。"),
    received_at: str = typer.Option(..., "--received-at", help="接收日期。"),
    sensitivity: str = typer.Option("low", "--sensitivity", help="敏感级别。"),
    large_file: bool = typer.Option(False, "--large-file", help="是否为大文件。"),
    original_location: str | None = typer.Option(None, "--original-location", help="原件位置。"),
    committable_original: bool = typer.Option(
        False,
        "--committable-original",
        help="是否允许提交原件。",
    ),
    related_ref: list[str] = typer.Option([], "--related-ref", help="关联需求或任务，可重复。"),
    retention: str | None = typer.Option(None, "--retention", help="保留或删除策略。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """登记材料，只写入脱敏索引，不复制原件。"""
    try:
        root = find_workspace_root(workspace_root)
        result = add_material(
            root,
            material_id=material_id,
            title=title,
            source=source,
            summary=summary,
            received_at=received_at,
            sensitivity=sensitivity,
            large_file=large_file,
            original_location=original_location,
            committable_original=committable_original,
            related_refs=related_ref,
            retention=retention,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@material_app.command("list")
def material_list(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出已登记材料。"""
    try:
        root = find_workspace_root(workspace_root)
        registry = read_material_registry(root)
        for entry in registry.materials:
            typer.echo(f"material {entry.id} {entry.title} source={entry.source}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@discovery_app.command("create")
def discovery_create(
    discovery_id: str = typer.Argument(..., help="发现记录 ID，例如 DISC-001。"),
    title: str = typer.Option(..., "--title", help="发现标题。"),
    material_ref: list[str] = typer.Option(..., "--material-ref", help="来源材料 ID，可重复。"),
    confirmed_fact: list[str] = typer.Option([], "--confirmed-fact", help="已确认事实，可重复。"),
    observation: list[str] = typer.Option([], "--observation", help="系统观察，可重复。"),
    inference: list[str] = typer.Option([], "--inference", help="AI 推断，可重复。"),
    assumption: list[str] = typer.Option([], "--assumption", help="假设，可重复。"),
    question: list[str] = typer.Option([], "--question", help="待用户确认问题，可重复。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    created_at: str | None = typer.Option(None, "--created-at", help="创建时间；默认等于更新时间。"),
    updated_at: str = typer.Option(..., "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 discovery 记录；它只记录观察和推断，不授权开发。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_discovery_package(
            root,
            discovery_id=discovery_id,
            title=title,
            material_refs=material_ref,
            updated_at=updated_at,
            confirmed_facts=confirmed_fact,
            system_observations=observation,
            ai_inferences=inference,
            assumptions=assumption,
            questions_for_user=question,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run)
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@intake_app.command("create")
def intake_create(
    requirement_id: str | None = typer.Argument(None, help="需求 ID，例如 REQ-20260702-001；省略则自动生成。"),
    title: str = typer.Option(..., "--title", help="需求标题。"),
    goal: str = typer.Option(..., "--goal", help="需求目标。"),
    acceptance: list[str] = typer.Option(..., "--acceptance", help="验收口径，可重复。"),
    material_ref: list[str] = typer.Option([], "--material-ref", help="来源材料 ID，可重复。"),
    discovery_ref: list[str] = typer.Option([], "--discovery-ref", help="来源 discovery ID，可重复。"),
    confirmed_fact: list[str] = typer.Option([], "--confirmed-fact", help="已确认事实，可重复。"),
    observation: list[str] = typer.Option([], "--observation", help="系统观察，可重复。"),
    inference: list[str] = typer.Option([], "--inference", help="AI 推断，可重复。"),
    assumption: list[str] = typer.Option([], "--assumption", help="假设，可重复。"),
    question: list[str] = typer.Option([], "--question", help="待用户确认问题，可重复。"),
    non_goal: list[str] = typer.Option([], "--non-goal", help="非目标，可重复。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    created_at: str | None = typer.Option(None, "--created-at", help="创建时间；默认等于更新时间。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间；默认当前时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 intake 草案；草案未确认前不是 readable requirement。"""
    try:
        root = find_workspace_root(workspace_root)
        timestamp = resolve_timestamp(updated_at or created_at)
        resolved_requirement_id = requirement_id or allocate_requirement_id(root, timestamp)
        context = RequirementTemplateContext(
            requirement_id=resolved_requirement_id,
            title=title,
            goal=goal,
            acceptance=acceptance,
            non_goals=non_goal,
            created_at=resolve_timestamp(created_at or timestamp),
            material_refs=material_ref,
            discovery_refs=discovery_ref,
            confirmed_facts=confirmed_fact,
            system_observations=observation,
            ai_inferences=inference,
            assumptions=assumption,
            questions_for_user=question,
            updated_at=resolve_timestamp(updated_at or timestamp),
        )
        result = create_intake_draft(root, context, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run)
        typer.echo(f"created requirement_id={resolved_requirement_id}")
        _refresh_generated_views(root, dry_run=dry_run)
    except (TemplateError, ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@intake_app.command("confirm")
def intake_confirm(
    requirement_id: str = typer.Argument(..., help="需求 ID，例如 REQ-20260702-001。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """确认 intake，使 requirement 进入 readable。"""
    try:
        root = find_workspace_root(workspace_root)
        result = confirm_intake(root, requirement_id, updated_at=updated_at, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)
