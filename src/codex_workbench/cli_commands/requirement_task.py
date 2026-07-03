from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from ..advice import task_command_advice_lines
from ..errors import WorkbenchError
from ..ids import allocate_requirement_id, allocate_task_id
from ..packages import (
    block_task,
    check_task_stage,
    close_requirement,
    create_task_implementation_document,
    create_requirement_package,
    create_task_review_document,
    create_task_package,
    obsolete_task,
    prepare_task,
    set_task_stage,
    update_task_impact,
    update_task_packet,
)
from ..task_context import (
    TASK_CONTEXT_SERVICE_CHECK_LIMIT,
    AbilityState,
    TaskContext,
    build_task_context,
    task_context_payload,
)
from ..templates import RequirementTemplateContext, TaskTemplateContext, TemplateError
from ..timeutils import resolve_timestamp
from ..workspace import find_workspace_root
from .common import (
    _build_impact_profile,
    _echo_markdown_template_hint,
    _echo_package_result,
    _exit_with_workbench_error,
    _refresh_generated_views,
)

requirement_app = typer.Typer(help="需求包工具。", no_args_is_help=True)
task_app = typer.Typer(help="任务包工具。", no_args_is_help=True)

@requirement_app.callback()
def requirement_callback() -> None:
    """requirement 命令组。"""

@task_app.callback()
def task_callback() -> None:
    """task 命令组。"""

@requirement_app.command("create")
def requirement_create(
    requirement_id: str | None = typer.Argument(None, help="需求 ID，例如 REQ-20260702-001；省略则自动生成。"),
    title: str = typer.Option(..., "--title", help="需求标题。"),
    goal: str = typer.Option(..., "--goal", help="需求目标。"),
    acceptance: list[str] = typer.Option(..., "--acceptance", help="验收口径，可重复。"),
    non_goal: list[str] = typer.Option([], "--non-goal", help="非目标，可重复。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    created_at: str | None = typer.Option(None, "--created-at", help="创建时间；默认等于更新时间。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间；默认当前时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 requirement package。"""
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
            updated_at=resolve_timestamp(updated_at or timestamp),
        )
        result = create_requirement_package(root, context, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run)
        typer.echo(f"created requirement_id={resolved_requirement_id}")
        _refresh_generated_views(root, dry_run=dry_run)
        _echo_markdown_template_hint()
    except (TemplateError, ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@requirement_app.command("close")
def requirement_close(
    requirement_id: str = typer.Argument(..., help="需求 ID，例如 REQ-20260702-001。"),
    note: str = typer.Option(..., "--note", help="用户确认需求关闭说明。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """关闭 requirement：只追加 requirement_closure confirmation。"""
    try:
        root = find_workspace_root(workspace_root)
        result = close_requirement(
            root,
            requirement_id,
            note=note,
            updated_at=updated_at,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("create")
def task_create(
    task_id: str | None = typer.Argument(None, help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001；省略则自动生成。"),
    requirement_id: str = typer.Option(..., "--requirement-id", help="所属需求 ID。"),
    title: str = typer.Option(..., "--title", help="任务标题。"),
    user_goal: str = typer.Option(..., "--user-goal", help="用户目标。"),
    done: list[str] = typer.Option(..., "--done", help="完成口径，可重复。"),
    next_step: str = typer.Option(..., "--next", help="下一步恢复提示。"),
    allowed_scope: list[str] = typer.Option([], "--allowed-scope", help="允许范围，可重复。"),
    not_allowed_scope: list[str] = typer.Option([], "--not-allowed-scope", help="非范围，可重复。"),
    service_ref: list[str] = typer.Option([], "--service-ref", help="相关服务标记，可重复。"),
    process_level: str = typer.Option("micro", "--process-level", help="流程显性化强度。"),
    risk_level: str = typer.Option("low", "--risk-level", help="风险等级。"),
    impact_action: str | None = typer.Option(None, "--impact-action", help="影响面画像：主要动作。"),
    impact_component: list[str] = typer.Option([], "--impact-component", help="影响面画像：组件线索，可重复。"),
    impact_environment: str | None = typer.Option(None, "--impact-environment", help="影响面画像：目标环境。"),
    impact_data_effect: str | None = typer.Option(None, "--impact-data-effect", help="影响面画像：数据影响。"),
    impact_external_effect: str | None = typer.Option(None, "--impact-external-effect", help="影响面画像：外部影响。"),
    impact_blast_radius: str | None = typer.Option(None, "--impact-blast-radius", help="影响面画像：影响半径。"),
    impact_reversibility: str | None = typer.Option(None, "--impact-reversibility", help="影响面画像：可回滚性。"),
    impact_contract_change: str | None = typer.Option(None, "--impact-contract-change", help="影响面画像：true/false/unknown。"),
    impact_security_or_permission: str | None = typer.Option(None, "--impact-security-or-permission", help="影响面画像：true/false/unknown。"),
    impact_verification_confidence: str | None = typer.Option(None, "--impact-verification-confidence", help="影响面画像：验证可信度。"),
    stage: str = typer.Option("draft", "--stage", help="初始任务阶段。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    created_at: str | None = typer.Option(None, "--created-at", help="创建时间；默认等于更新时间。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间；默认当前时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """创建 task package。"""
    try:
        root = find_workspace_root(workspace_root)
        timestamp = resolve_timestamp(updated_at or created_at)
        resolved_task_id = task_id or allocate_task_id(root, requirement_id, timestamp)
        context = TaskTemplateContext(
            task_id=resolved_task_id,
            title=title,
            requirement_id=requirement_id,
            user_goal=user_goal,
            done_means=done,
            current_next_step=next_step,
            created_at=resolve_timestamp(created_at or timestamp),
            updated_at=resolve_timestamp(updated_at or timestamp),
            allowed_scope=allowed_scope,
            not_allowed_scope=not_allowed_scope,
            process_level=process_level,
            risk_level=risk_level,
            impact_profile=_build_impact_profile(
                action=impact_action,
                components=impact_component,
                environment=impact_environment,
                data_effect=impact_data_effect,
                external_effect=impact_external_effect,
                blast_radius=impact_blast_radius,
                reversibility=impact_reversibility,
                contract_change=impact_contract_change,
                security_or_permission=impact_security_or_permission,
                verification_confidence=impact_verification_confidence,
            ),
            stage=stage,
            service_refs=service_ref,
        )
        result = create_task_package(root, context, dry_run=dry_run)
        created_paths = tuple(path for path in result.paths if path.parent.name == resolved_task_id)
        updated_paths = tuple(path for path in result.paths if path.parent.name == requirement_id)
        _echo_package_result(root, created_paths, dry_run=dry_run)
        _echo_package_result(root, updated_paths, dry_run=dry_run, verb="updated")
        typer.echo(f"created task_id={resolved_task_id}")
        _refresh_generated_views(root, dry_run=dry_run)
        _echo_markdown_template_hint()
    except (TemplateError, ValidationError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("update-packet")
def task_update_packet(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    next_step: str = typer.Option(..., "--next", help="task.yaml 中的下一步恢复提示。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """更新 task.yaml 中的 next_step 恢复提示。"""
    try:
        root = find_workspace_root(workspace_root)
        result = update_task_packet(
            root,
            task_id,
            next_step=next_step,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("set-stage")
def task_set_stage(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    stage: str = typer.Option(..., "--stage", help="目标阶段。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """更新 task.yaml 的主阶段，受 lifecycle guard 约束。"""
    try:
        root = find_workspace_root(workspace_root)
        result = set_task_stage(root, task_id, stage, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("check")
def task_check(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    to_stage: str = typer.Option(..., "--to", help="目标阶段。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """只读检查目标阶段门禁，不写 task.yaml。"""
    try:
        root = find_workspace_root(workspace_root)
        result = check_task_stage(root, task_id, to_stage)
        if result.allowed:
            typer.echo(f"task check allowed {result.task_id} -> {result.target_stage.value}")
            return
        reasons = ",".join(result.reason_codes)
        typer.echo(
            f"task check blocked {result.task_id} -> {result.target_stage.value}: {reasons}"
        )
        raise typer.Exit(1)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("context")
def task_context_command(
    task_ref: str = typer.Argument(..., help="任务标题、任务 ID 或 task.yaml 路径。"),
    output_format: str = typer.Option("text", "--format", help="输出格式：text/json。"),
    service_check_limit: int = typer.Option(
        TASK_CONTEXT_SERVICE_CHECK_LIMIT,
        "--service-check-limit",
        min=1,
        help="最多深入检查多少个唯一关联服务；默认 5，避免大项目变慢。",
    ),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """按任务名输出当前可做什么、缺什么、关联服务是否可接。"""
    try:
        if output_format not in {"text", "json"}:
            typer.echo(f"validation_error: unsupported_format: {output_format}", err=True)
            raise typer.Exit(2)
        root = find_workspace_root(workspace_root)
        context = build_task_context(root, task_ref, service_check_limit=service_check_limit)
        if output_format == "json":
            typer.echo(json.dumps(task_context_payload(context), ensure_ascii=False, indent=2))
            return
        typer.echo(_format_task_context(context))
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("prepare")
def task_prepare(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    working_scope: list[str] = typer.Option(
        ...,
        "--working-scope",
        help="implementation-ready 工作范围，可重复。",
    ),
    process_level: str | None = typer.Option(None, "--process-level", help="更新流程显性化强度。"),
    risk_level: str | None = typer.Option(None, "--risk-level", help="更新风险等级。"),
    impact_action: str | None = typer.Option(None, "--impact-action", help="影响面画像：主要动作。"),
    impact_component: list[str] = typer.Option([], "--impact-component", help="影响面画像：组件线索，可重复。"),
    impact_environment: str | None = typer.Option(None, "--impact-environment", help="影响面画像：目标环境。"),
    impact_data_effect: str | None = typer.Option(None, "--impact-data-effect", help="影响面画像：数据影响。"),
    impact_external_effect: str | None = typer.Option(None, "--impact-external-effect", help="影响面画像：外部影响。"),
    impact_blast_radius: str | None = typer.Option(None, "--impact-blast-radius", help="影响面画像：影响半径。"),
    impact_reversibility: str | None = typer.Option(None, "--impact-reversibility", help="影响面画像：可回滚性。"),
    impact_contract_change: str | None = typer.Option(None, "--impact-contract-change", help="影响面画像：true/false/unknown。"),
    impact_security_or_permission: str | None = typer.Option(None, "--impact-security-or-permission", help="影响面画像：true/false/unknown。"),
    impact_verification_confidence: str | None = typer.Option(None, "--impact-verification-confidence", help="影响面画像：验证可信度。"),
    impact_reason: str | None = typer.Option(None, "--impact-reason", help="风险画像更新原因。"),
    implementation_ref: str | None = typer.Option(
        None,
        "--implementation-ref",
        help="实现准入说明位置或摘要；推荐任务包本地 implementation.md。",
    ),
    review_ref: str | None = typer.Option(
        None,
        "--review-ref",
        help="高风险任务的 review 位置或摘要；推荐任务包本地 review.md；传入后标记 review done。",
    ),
    reviewer: str | None = typer.Option(
        None,
        "--reviewer",
        help="复核主体：subagent/user/human/external；高风险优先 subagent。",
    ),
    review_independent: bool = typer.Option(
        False,
        "--review-independent",
        help="声明 review 来自独立主体；high/critical 需要，个人工作台优先子代理复核。",
    ),
    risk_acceptance_note: str | None = typer.Option(
        None,
        "--risk-acceptance-note",
        help="高风险任务的风险接受说明。",
    ),
    likely_touchpoint: list[str] = typer.Option(
        [],
        "--likely-touchpoint",
        help="预计触点，可重复；不是白名单。",
    ),
    risk_trigger: list[str] = typer.Option(
        [],
        "--risk-trigger",
        help="暂停确认条件，可重复；不是白名单。",
    ),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """写入 implementation-ready 最小状态，不生成厚文档。"""
    try:
        root = find_workspace_root(workspace_root)
        result = prepare_task(
            root,
            task_id,
            working_scope=working_scope,
            process_level=process_level,
            risk_level=risk_level,
            impact_profile=_build_impact_profile(
                action=impact_action,
                components=impact_component,
                environment=impact_environment,
                data_effect=impact_data_effect,
                external_effect=impact_external_effect,
                blast_radius=impact_blast_radius,
                reversibility=impact_reversibility,
                contract_change=impact_contract_change,
                security_or_permission=impact_security_or_permission,
                verification_confidence=impact_verification_confidence,
                require_action=False,
            ),
            impact_reason=impact_reason,
            implementation_ref=implementation_ref,
            review_ref=review_ref,
            reviewer=reviewer,
            review_independent=review_independent,
            risk_acceptance_note=risk_acceptance_note,
            likely_touchpoints=likely_touchpoint,
            risk_triggers=risk_trigger,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


def _format_task_context(context: TaskContext) -> str:
    requirement_title = context.requirement.title if context.requirement else "<missing-or-invalid>"
    service_names = _format_task_service_refs(context)
    lines = [
        f"当前任务：{context.task.title}",
        f"所属需求：{requirement_title}",
        f"阶段：{context.task.stage.value} | 流程：{context.task.process_level.value} | 风险：{context.task.risk_level.value}",
        f"关联服务：{service_names}",
    ]
    if context.task.next_step:
        lines.append(f"下一步：{context.task.next_step}")

    lines.extend(["", "当前可做："])
    ability_labels = (
        ("read_only", "可以只读分析"),
        ("write_state", "可以写状态"),
        ("code_change", "可以改代码"),
        ("claim_done", "可以标记完成"),
        ("external_write", "可以外部写入"),
    )
    for name, label in ability_labels:
        lines.append(_format_ability_line(label, context.ability_matrix[name]))

    lines.extend(["", "服务现场："])
    if not context.services:
        lines.append("- 无")
    for service in context.services:
        purpose = f" | {service.purpose}" if service.purpose else ""
        lines.append(
            (
                f"- {service.name}：{service.path_state} | Git：{service.git_state} "
                f"| 入口：{_format_csv(service.entry_candidates)}{purpose}"
            )
        )
        if service.hard_gaps:
            lines.append(f"  阻断：{_format_csv(service.hard_gaps)}")
        if service.warnings:
            lines.append(f"  提醒：{_format_csv(service.warnings)}")
        if service.resolved_path:
            lines.append(f"  路径：{service.resolved_path}")
        scope_parts = []
        if service.git_status_scope:
            scope_parts.append(f"git_status={service.git_status_scope}")
        if service.service_relpath:
            scope_parts.append(f"service_relpath={service.service_relpath}")
        if scope_parts:
            lines.append(f"  Git 范围：{_format_csv(tuple(scope_parts))}")
        if service.dirty_count or service.untracked_count:
            lines.append(f"  已有变更：dirty={service.dirty_count} untracked={service.untracked_count}")
    if context.unchecked_service_refs:
        lines.append(
            f"- 还有 {len(context.unchecked_service_refs)} 个关联服务未展开："
            f"{_format_csv(context.unchecked_service_refs)}"
        )
        lines.append("  深入：按需运行 `service context <service-name>`")

    if context.next_actions:
        lines.extend(["", "下一步建议："])
        lines.extend(f"- {action}" for action in context.next_actions)
    command_advice = task_command_advice_lines(
        code_change_state=context.ability_matrix["code_change"].state,
        code_change_gaps=context.ability_matrix["code_change"].gaps,
        claim_done_state=context.ability_matrix["claim_done"].state,
        claim_done_gaps=context.ability_matrix["claim_done"].gaps,
        warnings=context.ability_matrix["code_change"].warnings,
    )
    if command_advice:
        lines.extend(["", "建议命令："])
        lines.extend(f"- {line}" for line in command_advice)
    return "\n".join(lines)


def _format_task_service_refs(context: TaskContext) -> str:
    if not context.services and not context.unchecked_service_refs:
        return "none"
    checked_names = tuple(service.name for service in context.services)
    displayed_names = _format_csv(checked_names)
    if not context.unchecked_service_refs:
        return displayed_names
    total = len(checked_names) + len(context.unchecked_service_refs)
    return (
        f"{displayed_names}"
        f"（共 {total}，已检查 {len(checked_names)}，未检查 {len(context.unchecked_service_refs)}）"
    )


def _format_ability_line(label: str, ability: AbilityState) -> str:
    line = f"- {label}：{_ability_state_label(ability.state)} - {ability.summary}"
    if ability.gaps:
        line += f"；阻断：{_format_csv(ability.gaps)}"
    if ability.warnings:
        line += f"；提醒：{_format_csv(ability.warnings)}"
    return line


def _ability_state_label(state: str) -> str:
    labels = {
        "allowed": "可以",
        "ready_to_mark_done": "需先标记",
        "cli_only": "只能通过 CLI",
        "after_stage_update": "需要先推进阶段",
        "needs_authorization": "需要授权",
        "blocked": "不可以",
    }
    return labels.get(state, state)


def _format_csv(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"

@task_app.command("impact-set")
def task_impact_set(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    process_level: str | None = typer.Option(None, "--process-level", help="流程显性化强度。"),
    risk_level: str | None = typer.Option(None, "--risk-level", help="风险等级。"),
    impact_action: str | None = typer.Option(None, "--impact-action", help="影响面画像：主要动作。"),
    impact_component: list[str] = typer.Option([], "--impact-component", help="影响面画像：组件线索，可重复。"),
    impact_environment: str | None = typer.Option(None, "--impact-environment", help="影响面画像：目标环境。"),
    impact_data_effect: str | None = typer.Option(None, "--impact-data-effect", help="影响面画像：数据影响。"),
    impact_external_effect: str | None = typer.Option(None, "--impact-external-effect", help="影响面画像：外部影响。"),
    impact_blast_radius: str | None = typer.Option(None, "--impact-blast-radius", help="影响面画像：影响半径。"),
    impact_reversibility: str | None = typer.Option(None, "--impact-reversibility", help="影响面画像：可回滚性。"),
    impact_contract_change: str | None = typer.Option(None, "--impact-contract-change", help="影响面画像：true/false/unknown。"),
    impact_security_or_permission: str | None = typer.Option(None, "--impact-security-or-permission", help="影响面画像：true/false/unknown。"),
    impact_verification_confidence: str | None = typer.Option(None, "--impact-verification-confidence", help="影响面画像：验证可信度。"),
    risk_trigger: list[str] = typer.Option([], "--risk-trigger", help="暂停确认条件，可重复；不是白名单。"),
    reason: str | None = typer.Option(None, "--reason", help="风险画像更新原因。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    updated_at: str | None = typer.Option(None, "--updated-at", help="更新时间；默认当前时间。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """更新 task 的风险画像、风险等级、流程档位和暂停条件。"""
    try:
        root = find_workspace_root(workspace_root)
        result = update_task_impact(
            root,
            task_id,
            process_level=process_level,
            risk_level=risk_level,
            impact_profile=_build_impact_profile(
                action=impact_action,
                components=impact_component,
                environment=impact_environment,
                data_effect=impact_data_effect,
                external_effect=impact_external_effect,
                blast_radius=impact_blast_radius,
                reversibility=impact_reversibility,
                contract_change=impact_contract_change,
                security_or_permission=impact_security_or_permission,
                verification_confidence=impact_verification_confidence,
                require_action=False,
            ),
            risk_triggers=risk_trigger,
            reason=reason or "",
            updated_at=updated_at,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("review-create")
def task_review_create(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """在任务包本地创建 review.md，并写入 review.ref。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_task_review_document(
            root,
            task_id,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
        _echo_markdown_template_hint()
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("implementation-create")
def task_implementation_create(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """在任务包本地创建 implementation.md，并写入 implementation.ref。"""
    try:
        root = find_workspace_root(workspace_root)
        result = create_task_implementation_document(
            root,
            task_id,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
        _echo_markdown_template_hint()
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("block")
def task_block(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    reason: str = typer.Option(..., "--reason", help="阻塞原因。"),
    blocked_by: str = typer.Option(..., "--blocked-by", help="阻塞方。"),
    resume_condition: str = typer.Option(..., "--resume-condition", help="恢复条件。"),
    resume_stage: str = typer.Option(..., "--resume-stage", help="恢复后阶段。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """将任务置为 blocked，并记录恢复条件。"""
    try:
        root = find_workspace_root(workspace_root)
        result = block_task(
            root,
            task_id,
            reason=reason,
            blocked_by=blocked_by,
            resume_condition=resume_condition,
            resume_stage=resume_stage,
            dry_run=dry_run,
        )
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)

@task_app.command("obsolete")
def task_obsolete(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    reason: str = typer.Option(..., "--reason", help="废弃原因。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将写入的文件。"),
) -> None:
    """将误建或废弃任务置为 obsolete，并保留说明。"""
    try:
        root = find_workspace_root(workspace_root)
        result = obsolete_task(root, task_id, reason=reason, dry_run=dry_run)
        _echo_package_result(root, result.paths, dry_run=dry_run, verb="updated")
        _refresh_generated_views(root, dry_run=dry_run)
    except (ValidationError, ValueError) as exc:
        typer.echo(f"validation_error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)
