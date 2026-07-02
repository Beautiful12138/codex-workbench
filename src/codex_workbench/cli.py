from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from . import __version__
from .archive import archive_version, list_archive_versions, plan_version_archive
from .errors import WorkbenchError
from .doctor import DoctorFinding, run_doctor
from .ids import allocate_requirement_id, allocate_task_id
from .index import check_generated_views, generate_index_views
from .materials import (
    add_material,
    confirm_intake,
    create_discovery_package,
    create_intake_draft,
    read_material_registry,
)
from .packages import (
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
    update_task_packet,
)
from .records import (
    classify_change,
    create_action_note,
    create_change_record,
    create_decision_record,
    create_suspicion_log,
)
from .schema import core_model_json_schemas
from .services import add_service, read_service_registry, service_status
from .templates import RequirementTemplateContext, TaskTemplateContext, TemplateError
from .timeutils import resolve_timestamp
from .validation import (
    apply_validation,
    create_evidence_record,
    set_handoff_status,
)
from .workspace import find_workspace_root


app = typer.Typer(help="个人本地 Codex workbench 工具。")
schema_app = typer.Typer(help="schema 工具。", no_args_is_help=True)
workspace_app = typer.Typer(help="工作区工具。", no_args_is_help=True)
requirement_app = typer.Typer(help="需求包工具。", no_args_is_help=True)
task_app = typer.Typer(help="任务包工具。", no_args_is_help=True)
service_app = typer.Typer(help="服务登记和只读状态工具。", no_args_is_help=True)
material_app = typer.Typer(help="材料登记工具。", no_args_is_help=True)
discovery_app = typer.Typer(help="发现记录工具。", no_args_is_help=True)
intake_app = typer.Typer(help="intake 草案和确认工具。", no_args_is_help=True)
evidence_app = typer.Typer(help="验证证据工具。", no_args_is_help=True)
validation_app = typer.Typer(help="验证结论工具。", no_args_is_help=True)
handoff_app = typer.Typer(help="用户验收交接工具。", no_args_is_help=True)
action_app = typer.Typer(help="非任务动作记录工具。", no_args_is_help=True)
change_app = typer.Typer(help="正式范围变化记录工具。", no_args_is_help=True)
decision_app = typer.Typer(help="冷路径长期决策记录工具。", no_args_is_help=True)
suspicion_app = typer.Typer(help="疑点线索记录工具。", no_args_is_help=True)
index_app = typer.Typer(help="生成 CURRENT、索引和恢复视图工具。", no_args_is_help=True)
doctor_app = typer.Typer(help="工作区健康检查工具。", no_args_is_help=True)
archive_app = typer.Typer(help="版本归档工具。", no_args_is_help=True)
MARKDOWN_TEMPLATE_HINT = (
    "markdown_template_hint: Markdown 模板只是起稿骨架，用来稍微统一格式；"
    "标题、章节和表达方式可按当前任务自由删改。"
)
app.add_typer(schema_app, name="schema")
app.add_typer(workspace_app, name="workspace")
app.add_typer(requirement_app, name="requirement")
app.add_typer(task_app, name="task")
app.add_typer(service_app, name="service")
app.add_typer(material_app, name="material")
app.add_typer(discovery_app, name="discovery")
app.add_typer(intake_app, name="intake")
app.add_typer(evidence_app, name="evidence")
app.add_typer(validation_app, name="validation")
app.add_typer(handoff_app, name="handoff")
app.add_typer(action_app, name="action")
app.add_typer(change_app, name="change")
app.add_typer(decision_app, name="decision")
app.add_typer(suspicion_app, name="suspicion")
app.add_typer(index_app, name="index")
app.add_typer(doctor_app, name="doctor")
app.add_typer(archive_app, name="archive")


@schema_app.callback()
def schema_callback() -> None:
    """schema 命令组。"""


@workspace_app.callback()
def workspace_callback() -> None:
    """工作区命令组。"""


@requirement_app.callback()
def requirement_callback() -> None:
    """requirement 命令组。"""


@task_app.callback()
def task_callback() -> None:
    """task 命令组。"""


@service_app.callback()
def service_callback() -> None:
    """service 命令组。"""


@material_app.callback()
def material_callback() -> None:
    """material 命令组。"""


@discovery_app.callback()
def discovery_callback() -> None:
    """discovery 命令组。"""


@intake_app.callback()
def intake_callback() -> None:
    """intake 命令组。"""


@evidence_app.callback()
def evidence_callback() -> None:
    """evidence 命令组。"""


@validation_app.callback()
def validation_callback() -> None:
    """validation 命令组。"""


@handoff_app.callback()
def handoff_callback() -> None:
    """handoff 命令组。"""


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


@index_app.callback()
def index_callback() -> None:
    """index 命令组。"""


@doctor_app.callback()
def doctor_callback() -> None:
    """doctor 命令组。"""


@archive_app.callback()
def archive_callback() -> None:
    """archive 命令组。"""


@app.command()
def version() -> None:
    """打印包版本。"""
    typer.echo(f"codex-workbench {__version__}")


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


@task_app.command("prepare")
def task_prepare(
    task_id: str = typer.Argument(..., help="任务 ID，例如 REQ-20260702-001-TASK-20260702-001。"),
    working_scope: list[str] = typer.Option(
        ...,
        "--working-scope",
        help="implementation-ready 工作范围，可重复。",
    ),
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
            implementation_ref=implementation_ref,
            review_ref=review_ref,
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


@service_app.command("add")
def service_add(
    name: str = typer.Argument(..., help="服务名，例如 api。"),
    local_path: Path = typer.Option(..., "--path", help="服务本地路径。"),
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
        if status.branch:
            line += f" branch={status.branch}"
        if status.head:
            line += f" head={status.head}"
        if status.git_state == "git":
            line += f" dirty={status.dirty_count} untracked={status.untracked_count}"
        typer.echo(line)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


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


def _build_impact_profile(
    *,
    action: str | None,
    components: list[str],
    environment: str | None,
    data_effect: str | None,
    external_effect: str | None,
    blast_radius: str | None,
    reversibility: str | None,
    contract_change: str | None,
    security_or_permission: str | None,
    verification_confidence: str | None,
) -> dict[str, object] | None:
    has_profile_input = any(
        (
            action,
            components,
            environment,
            data_effect,
            external_effect,
            blast_radius,
            reversibility,
            contract_change,
            security_or_permission,
            verification_confidence,
        )
    )
    if not has_profile_input:
        return None
    if not action or not action.strip():
        raise ValueError("impact_profile_requires_action")

    return {
        "action": action.strip(),
        "component_signals": [item.strip() for item in components if item.strip()],
        "environment": (environment or "unknown").strip(),
        "data_effect": (data_effect or "none").strip(),
        "external_effect": (external_effect or "none").strip(),
        "blast_radius": (blast_radius or "unknown").strip(),
        "reversibility": (reversibility or "unknown").strip(),
        "contract_change": _parse_impact_truth(contract_change),
        "security_or_permission": _parse_impact_truth(security_or_permission),
        "verification_confidence": (verification_confidence or "unclear").strip(),
    }


def _parse_impact_truth(value: str | None) -> bool | str:
    if value is None:
        return "unknown"
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    if normalized == "unknown":
        return "unknown"
    raise ValueError(f"invalid_impact_truth: {value}")


def _echo_package_result(
    root: Path,
    paths: tuple[Path, ...],
    *,
    dry_run: bool,
    verb: str = "created",
) -> None:
    verb = "dry-run" if dry_run else verb
    for path in paths:
        typer.echo(f"{verb} {path.relative_to(root).as_posix()}")


def _echo_markdown_template_hint() -> None:
    typer.echo(MARKDOWN_TEMPLATE_HINT)


def _refresh_generated_views(root: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    generate_index_views(root, dry_run=False)


def _echo_index_check(result) -> None:
    if result.clean:
        typer.echo("index clean")
        return
    for message in result.messages:
        typer.echo(message, err=True)
    raise typer.Exit(1)


def _echo_index_conflicts(conflicts: list[str]) -> None:
    for conflict in conflicts:
        typer.echo(f"conflict: {conflict}", err=True)


def _format_doctor_finding(finding: DoctorFinding) -> str:
    location = f" {finding.path}" if finding.path else ""
    subject = f" [{finding.subject}]" if finding.subject else ""
    return f"{finding.severity} {finding.code}{location}{subject}: {finding.message}"


def _exit_with_workbench_error(exc: WorkbenchError) -> None:
    typer.echo(f"{exc.code.value}: {exc.message}", err=True)
    raise typer.Exit(exc.exit_code) from exc


def main() -> None:
    app()
