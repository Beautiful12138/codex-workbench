from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml
from .models import RequirementState, TaskStage, TaskState, ValidationStatus
from .packages import TaskStageCheckResult, check_task_stage
from .refs import validate_package_ref
from .services import ServiceContext, service_context
from .workspace import resolve_workspace_path


HARD_SERVICE_GAPS = {
    "path_missing",
    "empty_service_dir",
    "service_path_is_file",
}
TASK_CONTEXT_SERVICE_CHECK_LIMIT = 5


@dataclass(frozen=True)
class AbilityState:
    state: str
    summary: str
    gaps: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskServiceView:
    name: str
    registry_state: str
    purpose: str | None
    notes: str | None
    resolved_path: Path | None
    path_state: str
    visible_file_count: int
    visible_file_count_limit_reached: bool
    git_state: str
    git_root: Path | None = None
    service_relpath: str | None = None
    git_status_scope: str | None = None
    git_error: str | None = None
    branch: str | None = None
    head: str | None = None
    dirty_count: int = 0
    untracked_count: int = 0
    entry_candidates: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def hard_gaps(self) -> tuple[str, ...]:
        return _service_hard_gaps(self.gaps)

    @property
    def warnings(self) -> tuple[str, ...]:
        return _service_gap_warnings(self.gaps)


@dataclass(frozen=True)
class TaskContext:
    task: TaskState
    task_path: Path
    requirement: RequirementState | None
    requirement_path: Path | None
    services: tuple[TaskServiceView, ...]
    unchecked_service_refs: tuple[str, ...]
    ability_matrix: dict[str, AbilityState]
    next_actions: tuple[str, ...]


def build_task_context(
    workspace_root: str | Path,
    task_ref: str,
    *,
    service_check_limit: int = TASK_CONTEXT_SERVICE_CHECK_LIMIT,
) -> TaskContext:
    root = Path(workspace_root).expanduser().resolve()
    task_path, task = _resolve_task(root, task_ref)
    requirement_path, requirement = _load_requirement(root, task.requirement_id)
    services, unchecked_service_refs = _load_task_services(root, task, service_check_limit=service_check_limit)
    in_progress_check = check_task_stage(root, task.id, TaskStage.IN_PROGRESS.value)
    done_check = check_task_stage(root, task.id, TaskStage.DONE.value)
    service_gaps = _hard_service_gaps(services)
    warnings = _service_warnings(services)
    if unchecked_service_refs:
        service_gaps = tuple(dict.fromkeys((*service_gaps, "service_check_limited")))
        warnings = tuple(dict.fromkeys(("service_check_limited", *warnings)))
    context_gaps = ("requirement_missing_or_invalid",) if requirement is None else ()
    ability_matrix = _build_ability_matrix(
        task,
        in_progress_check=in_progress_check,
        done_check=done_check,
        service_gaps=service_gaps,
        context_gaps=context_gaps,
        warnings=warnings,
    )
    return TaskContext(
        task=task,
        task_path=task_path,
        requirement=requirement,
        requirement_path=requirement_path,
        services=services,
        unchecked_service_refs=unchecked_service_refs,
        ability_matrix=ability_matrix,
        next_actions=_next_actions(task, ability_matrix, service_gaps),
    )


def task_context_payload(context: TaskContext) -> dict[str, object]:
    return {
        "task": {
            "id": context.task.id,
            "title": context.task.title,
            "stage": context.task.stage.value,
            "process_level": context.task.process_level.value,
            "risk_level": context.task.risk_level.value,
            "next_step": context.task.next_step,
            "path": str(context.task_path),
            "service_refs": list(context.task.service_refs),
        },
        "requirement": _requirement_payload(context),
        "ability_matrix": {
            name: {
                "state": ability.state,
                "summary": ability.summary,
                "gaps": list(ability.gaps),
                "warnings": list(ability.warnings),
            }
            for name, ability in context.ability_matrix.items()
        },
        "services": [_service_payload(service) for service in context.services],
        "unchecked_service_refs": list(context.unchecked_service_refs),
        "next_actions": list(context.next_actions),
    }


def _resolve_task(root: Path, task_ref: str) -> tuple[Path, TaskState]:
    cleaned_ref = task_ref.strip()
    if not cleaned_ref:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, "missing_task_ref", exit_code=2)

    active_root = resolve_workspace_path(root, "docs/active")
    explicit_path = _explicit_task_path(root, cleaned_ref)
    if explicit_path:
        if not explicit_path.exists():
            raise WorkbenchError(
                ErrorCode.VALIDATION_ERROR,
                f"task_path_missing: {explicit_path}",
                exit_code=2,
            )
        _ensure_active_task_path(active_root, explicit_path)
        return _load_task_from_path(explicit_path)

    direct_path = _direct_task_path(active_root, cleaned_ref)
    if direct_path and direct_path.exists():
        return _load_task_from_path(direct_path, expected_id=cleaned_ref)

    matches: list[tuple[Path, TaskState]] = []
    for task_path in sorted(active_root.glob("*/task.yaml")):
        try:
            path, task = _load_task_from_path(task_path)
        except WorkbenchError:
            continue
        if task.id == cleaned_ref or task.title.casefold() == cleaned_ref.casefold():
            matches.append((path, task))

    if not matches:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_not_found: {cleaned_ref}",
            exit_code=2,
        )
    if len(matches) > 1:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"ambiguous_task_ref: {cleaned_ref}",
            exit_code=2,
        )
    return matches[0]


def _direct_task_path(active_root: Path, task_ref: str) -> Path | None:
    try:
        clean_ref = validate_package_ref(task_ref)
    except WorkbenchError:
        return None
    return active_root / clean_ref / "task.yaml"


def _explicit_task_path(root: Path, task_ref: str) -> Path | None:
    candidate = Path(task_ref)
    if candidate.name != "task.yaml":
        return None
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.PATH_OUTSIDE_WORKSPACE,
            f"path_outside_workspace: {task_ref}",
            exit_code=2,
        ) from exc
    return resolved


def _ensure_active_task_path(active_root: Path, task_path: Path) -> None:
    try:
        relative = task_path.relative_to(active_root)
    except ValueError as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_path_not_active: {task_path}",
            exit_code=2,
        ) from exc
    if len(relative.parts) != 2 or relative.parts[1] != "task.yaml":
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_path_not_active: {task_path}",
            exit_code=2,
        )


def _load_task_from_path(task_path: Path, expected_id: str | None = None) -> tuple[Path, TaskState]:
    try:
        task = TaskState.model_validate(read_yaml(task_path))
    except (ValidationError, WorkbenchError) as exc:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_task_package: {task_path.parent.name}",
            exit_code=2,
        ) from exc
    if expected_id and task.id != expected_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_id_mismatch: expected={expected_id} actual={task.id}",
            exit_code=2,
        )
    if task_path.parent.name != task.id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"task_path_id_mismatch: path={task_path.parent.name} yaml={task.id}",
            exit_code=2,
        )
    return task_path, task


def _load_requirement(root: Path, requirement_id: str) -> tuple[Path | None, RequirementState | None]:
    requirement_path = resolve_workspace_path(root, f"docs/active/{requirement_id}/requirement.yaml")
    if not requirement_path.exists():
        return None, None
    try:
        requirement = RequirementState.model_validate(read_yaml(requirement_path))
    except (ValidationError, WorkbenchError):
        return requirement_path, None
    if requirement.id != requirement_id:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"requirement_path_id_mismatch: path={requirement_id} yaml={requirement.id}",
            exit_code=2,
        )
    return requirement_path, requirement


def _load_task_services(
    root: Path,
    task: TaskState,
    *,
    service_check_limit: int,
) -> tuple[tuple[TaskServiceView, ...], tuple[str, ...]]:
    services: list[TaskServiceView] = []
    service_refs = _unique_service_refs(task.service_refs)
    checked_service_refs = service_refs[:service_check_limit]
    unchecked_service_refs = service_refs[service_check_limit:]
    for service_ref in checked_service_refs:
        try:
            services.append(_service_view(service_context(root, service_ref)))
        except WorkbenchError as exc:
            if exc.message.startswith("unknown_service"):
                services.append(
                    TaskServiceView(
                        name=service_ref,
                        registry_state="missing",
                        purpose=None,
                        notes=None,
                        resolved_path=None,
                        path_state="missing",
                        visible_file_count=0,
                        visible_file_count_limit_reached=False,
                        git_state="missing",
                        gaps=(f"unknown_service_ref:{service_ref}",),
                    )
                )
                continue
            raise
    return tuple(services), tuple(unchecked_service_refs)


def _unique_service_refs(service_refs: list[str]) -> tuple[str, ...]:
    unique_refs: list[str] = []
    seen: set[str] = set()
    for raw_ref in service_refs:
        service_ref = str(raw_ref).strip()
        if not service_ref or service_ref in seen:
            continue
        unique_refs.append(service_ref)
        seen.add(service_ref)
    return tuple(unique_refs)


def _service_view(context: ServiceContext) -> TaskServiceView:
    return TaskServiceView(
        name=context.name,
        registry_state=context.registry_state,
        purpose=context.purpose,
        notes=context.notes,
        resolved_path=context.resolved_path,
        path_state=context.path_state,
        visible_file_count=context.visible_file_count,
        visible_file_count_limit_reached=context.visible_file_count_limit_reached,
        git_state=context.git_state,
        git_root=context.git_root,
        service_relpath=context.service_relpath,
        git_status_scope=context.git_status_scope,
        git_error=context.git_error,
        branch=context.branch,
        head=context.head,
        dirty_count=context.dirty_count,
        untracked_count=context.untracked_count,
        entry_candidates=context.entry_candidates,
        gaps=context.gaps,
    )


def _hard_service_gaps(services: tuple[TaskServiceView, ...]) -> tuple[str, ...]:
    gaps: list[str] = []
    for service in services:
        gaps.extend(_service_hard_gaps(service.gaps))
    return tuple(dict.fromkeys(gaps))


def _service_warnings(services: tuple[TaskServiceView, ...]) -> tuple[str, ...]:
    warnings: list[str] = []
    hard_gaps = set(_hard_service_gaps(services))
    for service in services:
        warnings.extend(gap for gap in _service_gap_warnings(service.gaps) if gap not in hard_gaps)
    return tuple(dict.fromkeys(warnings))


def _service_hard_gaps(gaps: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(gap for gap in gaps if gap in HARD_SERVICE_GAPS or gap.startswith("unknown_service_ref"))


def _service_gap_warnings(gaps: tuple[str, ...]) -> tuple[str, ...]:
    hard_gaps = set(_service_hard_gaps(gaps))
    return tuple(gap for gap in gaps if gap not in hard_gaps)


def _build_ability_matrix(
    task: TaskState,
    *,
    in_progress_check: TaskStageCheckResult,
    done_check: TaskStageCheckResult,
    service_gaps: tuple[str, ...],
    context_gaps: tuple[str, ...],
    warnings: tuple[str, ...],
) -> dict[str, AbilityState]:
    code_gaps = tuple(dict.fromkeys((*in_progress_check.reason_codes, *service_gaps, *context_gaps)))
    if task.stage is TaskStage.IN_PROGRESS and not code_gaps:
        code_change = AbilityState(
            "allowed",
            "任务已进入执行态，当前开工事实满足。",
            warnings=warnings,
        )
    elif not code_gaps:
        code_change = AbilityState(
            "after_stage_update",
            "先用 CLI 把任务推进到 in_progress，再开始代码修改。",
            ("task_not_in_progress",),
            warnings,
        )
    else:
        code_change = AbilityState("blocked", "缺少开工事实，先补上下文或服务路径。", code_gaps, warnings)

    if task.stage is TaskStage.DONE and done_check.allowed:
        claim_done = AbilityState("allowed", "任务已处于 done，且完成事实满足。")
    elif done_check.allowed:
        claim_done = AbilityState("ready_to_mark_done", "完成条件已满足，下一步应用 CLI 标记 done。")
    else:
        claim_done = AbilityState(
            "blocked",
            "还不能称为完成，需要验证、证据或交接事实。",
            done_check.reason_codes,
        )
    return {
        "read_only": AbilityState("allowed", "可以阅读、分析、定位和解释。"),
        "write_state": AbilityState("cli_only", "状态写入只通过 Workbench CLI。"),
        "code_change": code_change,
        "claim_done": claim_done,
        "external_write": AbilityState(
            "needs_authorization",
            "数据库、部署、外部系统写入需要明确授权。",
            ("needs_explicit_authorization",),
        ),
    }


def _next_actions(
    task: TaskState,
    ability_matrix: dict[str, AbilityState],
    service_gaps: tuple[str, ...],
) -> tuple[str, ...]:
    actions: list[str] = []
    code_state = ability_matrix["code_change"].state
    if service_gaps:
        actions.append("确认服务真实路径或改用已存在代码目录")
    if "missing_implementation_ready" in ability_matrix["code_change"].gaps:
        actions.append("用 task prepare 补最小工作范围")
    if code_state == "after_stage_update":
        actions.append("用 task set-stage 进入执行态")
    if code_state == "allowed":
        actions.append("继续围绕任务目标做最小修改并验证")
    if task.stage is not TaskStage.IN_PROGRESS and not actions:
        actions.append("确认是否进入执行态")
    if (
        ability_matrix["claim_done"].state == "blocked"
        and (
            task.stage is TaskStage.VERIFICATION_PENDING
            or task.validation.status is not ValidationStatus.NOT_STARTED
        )
    ):
        actions.append("完成前补验证证据")
    return tuple(dict.fromkeys(actions))


def _requirement_payload(context: TaskContext) -> dict[str, object]:
    if context.requirement is None:
        return {
            "id": context.task.requirement_id,
            "title": None,
            "path": str(context.requirement_path) if context.requirement_path else None,
            "state": "missing_or_invalid",
        }
    return {
        "id": context.requirement.id,
        "title": context.requirement.title,
        "path": str(context.requirement_path) if context.requirement_path else None,
        "state": "loaded",
    }


def _service_payload(service: TaskServiceView) -> dict[str, object]:
    return {
        "name": service.name,
        "registry_state": service.registry_state,
        "purpose": service.purpose,
        "notes": service.notes,
        "resolved_path": str(service.resolved_path) if service.resolved_path else None,
        "path_state": service.path_state,
        "visible_file_count": service.visible_file_count,
        "visible_file_count_limit_reached": service.visible_file_count_limit_reached,
        "git_state": service.git_state,
        "git_root": str(service.git_root) if service.git_root else None,
        "service_relpath": service.service_relpath,
        "git_status_scope": service.git_status_scope,
        "git_error": service.git_error,
        "branch": service.branch,
        "head": service.head,
        "dirty_count": service.dirty_count,
        "untracked_count": service.untracked_count,
        "entry_candidates": list(service.entry_candidates),
        "gaps": list(service.gaps),
        "hard_gaps": list(service.hard_gaps),
        "warnings": list(service.warnings),
    }
