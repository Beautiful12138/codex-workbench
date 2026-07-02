from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
import re
from typing import Any

import yaml


ACTION_NOTE_TYPES = {"maintenance_action", "ops_action", "ephemeral_check"}
ACTION_NOTE_STATUSES = {"planned", "executed", "partial", "failed", "reverted"}


class TemplateError(ValueError):
    pass


def _require(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise TemplateError(f"缺少必填模板字段：{field_name}")
    return cleaned


def _list(items: list[str] | None) -> list[str]:
    return [item.strip() for item in items or [] if item.strip()]


@dataclass(frozen=True)
class TaskTemplateContext:
    task_id: str
    title: str
    requirement_id: str
    user_goal: str
    done_means: list[str]
    current_next_step: str
    created_at: str
    updated_at: str
    allowed_scope: list[str] = field(default_factory=list)
    not_allowed_scope: list[str] = field(default_factory=list)
    process_level: str = "micro"
    risk_level: str = "low"
    stage: str = "draft"
    services_file: str = "../../../services/registry.yaml"
    service_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.task_id, "task_id")
        _require(self.title, "title")
        _require(self.requirement_id, "requirement_id")
        _require(self.user_goal, "user_goal")
        _require(self.current_next_step, "current_next_step")
        _require(self.created_at, "created_at")
        _require(self.updated_at, "updated_at")
        if not _list(self.done_means):
            raise TemplateError("缺少必填模板字段：done_means")


@dataclass(frozen=True)
class RequirementTemplateContext:
    requirement_id: str
    title: str
    goal: str
    acceptance: list[str]
    created_at: str
    updated_at: str
    non_goals: list[str] = field(default_factory=list)
    task_refs: list[str] = field(default_factory=list)
    readiness_status: str | None = None
    readiness_confirmed_by_user: bool = False
    material_refs: list[str] = field(default_factory=list)
    discovery_refs: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    system_observations: list[str] = field(default_factory=list)
    ai_inferences: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    questions_for_user: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.requirement_id, "requirement_id")
        _require(self.title, "title")
        _require(self.goal, "goal")
        _require(self.created_at, "created_at")
        _require(self.updated_at, "updated_at")
        if not _list(self.acceptance):
            raise TemplateError("缺少必填模板字段：acceptance")


@dataclass(frozen=True)
class EvidenceTemplateContext:
    evidence_id: str
    task_id: str
    conclusion: str
    key_outputs: list[str]
    updated_at: str
    unverified_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.evidence_id, "evidence_id")
        _require(self.task_id, "task_id")
        _require(self.conclusion, "conclusion")
        _require(self.updated_at, "updated_at")
        if not _list(self.key_outputs):
            raise TemplateError("缺少必填模板字段：key_outputs")


@dataclass(frozen=True)
class TaskDocumentTemplateContext:
    task_id: str

    def __post_init__(self) -> None:
        _require(self.task_id, "task_id")


@dataclass(frozen=True)
class ActionNoteTemplateContext:
    action_id: str
    title: str
    summary: str
    action_type: str
    updated_at: str
    status: str = "executed"
    authorization: str | None = None
    target: str | None = None
    result: str | None = None
    related_refs: list[str] = field(default_factory=list)
    side_effect_summary: str = "no_side_effect"
    rollback_hint: str = "no_rollback_needed"

    def __post_init__(self) -> None:
        _require(self.action_id, "action_id")
        _require(self.title, "title")
        _require(self.summary, "summary")
        _require(self.action_type, "action_type")
        if self.action_type not in ACTION_NOTE_TYPES:
            raise TemplateError("invalid_action_type")
        _require(self.status, "status")
        if self.status not in ACTION_NOTE_STATUSES:
            raise TemplateError("invalid_action_status")
        _require(self.updated_at, "updated_at")
        _require(self.side_effect_summary, "side_effect_summary")
        _require(self.rollback_hint, "rollback_hint")


@dataclass(frozen=True)
class ChangeRecordTemplateContext:
    change_id: str
    title: str
    updated_at: str
    change_kind: str
    changed_area: str
    reason: str
    impact: str
    handling: str
    related_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.change_id, "change_id")
        _require(self.title, "title")
        _require(self.updated_at, "updated_at")
        _require(self.change_kind, "change_kind")
        _require(self.changed_area, "changed_area")
        _require(self.reason, "reason")
        _require(self.impact, "impact")
        _require(self.handling, "handling")


@dataclass(frozen=True)
class DecisionRecordTemplateContext:
    decision_id: str
    title: str
    updated_at: str
    cold_path_reason: str
    context: str
    decision: str
    impact: str
    status: str = "active"

    def __post_init__(self) -> None:
        _require(self.decision_id, "decision_id")
        _require(self.title, "title")
        _require(self.updated_at, "updated_at")
        _require(self.cold_path_reason, "cold_path_reason")
        _require(self.context, "context")
        _require(self.decision, "decision")
        _require(self.impact, "impact")
        _require(self.status, "status")


@dataclass(frozen=True)
class SuspicionTemplateContext:
    suspicion_id: str
    title: str
    updated_at: str
    location_or_subject: str
    confirmed_facts: list[str]
    ai_inferences: list[str]
    current_task_impact: str
    suggested_handling: str
    assumptions: list[str] = field(default_factory=list)
    related_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.suspicion_id, "suspicion_id")
        _require(self.title, "title")
        _require(self.updated_at, "updated_at")
        _require(self.location_or_subject, "location_or_subject")
        _require(self.current_task_impact, "current_task_impact")
        _require(self.suggested_handling, "suggested_handling")
        if not _list(self.confirmed_facts):
            raise TemplateError("缺少必填模板字段：confirmed_facts")
        if not _list(self.ai_inferences):
            raise TemplateError("缺少必填模板字段：ai_inferences")


def render_task_package(context: TaskTemplateContext) -> dict[str, str]:
    base = f"docs/active/{context.task_id}"
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.task_id,
        "requirement_id": context.requirement_id,
        "title": context.title,
        "created_at": context.created_at,
        "updated_at": context.updated_at,
        "stage": context.stage,
        "next_step": context.current_next_step,
        "process_level": context.process_level,
        "risk_level": context.risk_level,
        "service_refs": _list(context.service_refs),
        "validation": {"status": "not_started"},
    }
    return {
        f"{base}/task.yaml": _yaml(yaml_payload),
        f"{base}/task.md": _ensure_final_newline(_render_task_markdown(context)),
    }


def render_requirement_package(context: RequirementTemplateContext) -> dict[str, str]:
    base = f"docs/active/{context.requirement_id}"
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.requirement_id,
        "title": context.title,
        "goal": context.goal,
        "created_at": context.created_at,
        "updated_at": context.updated_at,
        "acceptance": _list(context.acceptance),
    }
    if _list(context.non_goals):
        yaml_payload["non_goals"] = _list(context.non_goals)
    if _list(context.task_refs):
        yaml_payload["task_refs"] = _list(context.task_refs)
    if context.readiness_status:
        yaml_payload["readiness"] = {
            "status": context.readiness_status,
            "confirmed_by_user": context.readiness_confirmed_by_user,
            "material_refs": _list(context.material_refs),
            "discovery_refs": _list(context.discovery_refs),
        }
    knowledge = _knowledge_payload(context)
    if knowledge:
        yaml_payload["knowledge"] = knowledge
    return {
        f"{base}/requirement.yaml": _yaml(yaml_payload),
        f"{base}/requirement.md": _ensure_final_newline(_render_requirement_markdown(context)),
    }


def render_evidence_document(context: EvidenceTemplateContext) -> dict[str, str]:
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.evidence_id,
        "task_id": context.task_id,
        "conclusion": context.conclusion,
        "key_outputs": _list(context.key_outputs),
        "unverified_items": _list(context.unverified_items),
    }
    return {
        f"docs/active/{context.task_id}/evidence.yaml": _yaml(yaml_payload),
        f"docs/active/{context.task_id}/evidence.md": _ensure_final_newline(
            _render_evidence_markdown(context)
        ),
    }


def render_review_document(context: TaskDocumentTemplateContext) -> dict[str, str]:
    return {
        f"docs/active/{context.task_id}/review.md": _ensure_final_newline(
            _render_work_product_template("review.md", {"task_id": context.task_id})
        )
    }


def render_implementation_document(context: TaskDocumentTemplateContext) -> dict[str, str]:
    return {
        f"docs/active/{context.task_id}/implementation.md": _ensure_final_newline(
            _render_work_product_template("implementation.md", {"task_id": context.task_id})
        )
    }


def render_action_note(context: ActionNoteTemplateContext) -> dict[str, str]:
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.action_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "summary": context.summary,
        "action_type": context.action_type,
        "status": context.status,
        "side_effect_summary": context.side_effect_summary,
        "rollback_hint": context.rollback_hint,
    }
    if context.authorization:
        yaml_payload["authorization"] = context.authorization
    if context.target:
        yaml_payload["target"] = context.target
    if context.result:
        yaml_payload["result"] = context.result
    if _list(context.related_refs):
        yaml_payload["related_refs"] = _list(context.related_refs)
    return {
        f"docs/actions/{context.action_id}.yaml": _yaml(yaml_payload),
        f"docs/actions/{context.action_id}.md": _ensure_final_newline(
            _render_work_product_template(
                "action.md",
                {
                    "action_id": context.action_id,
                    "title": context.title,
                },
            )
        ),
    }


def render_change_record(context: ChangeRecordTemplateContext) -> dict[str, str]:
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.change_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "change_kind": context.change_kind,
        "changed_area": context.changed_area,
        "reason": context.reason,
        "impact": context.impact,
        "handling": context.handling,
    }
    if _list(context.related_refs):
        yaml_payload["related_refs"] = _list(context.related_refs)
    return {
        f"docs/changes/{context.change_id}.yaml": _yaml(yaml_payload),
        f"docs/changes/{context.change_id}.md": _ensure_final_newline(
            _render_work_product_template(
                "change.md",
                {
                    "change_id": context.change_id,
                    "title": context.title,
                },
            )
        ),
    }


def render_decision_record(context: DecisionRecordTemplateContext) -> dict[str, str]:
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.decision_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "cold_path_reason": context.cold_path_reason,
        "status": context.status,
        "context": context.context,
        "decision": context.decision,
        "impact": context.impact,
    }
    return {
        f"docs/decisions/{context.decision_id}.yaml": _yaml(yaml_payload),
        f"docs/decisions/{context.decision_id}.md": _ensure_final_newline(
            _render_work_product_template(
                "decision.md",
                {
                    "decision_id": context.decision_id,
                    "title": context.title,
                },
            )
        ),
    }


def render_suspicion_log(context: SuspicionTemplateContext) -> dict[str, str]:
    yaml_payload: dict[str, Any] = {
        "schema_version": "0.1",
        "id": context.suspicion_id,
        "title": context.title,
        "updated_at": context.updated_at,
        "location_or_subject": context.location_or_subject,
        "confirmed_facts": _list(context.confirmed_facts),
        "ai_inferences": _list(context.ai_inferences),
        "current_task_impact": context.current_task_impact,
        "suggested_handling": context.suggested_handling,
    }
    if _list(context.assumptions):
        yaml_payload["assumptions"] = _list(context.assumptions)
    if _list(context.related_refs):
        yaml_payload["related_refs"] = _list(context.related_refs)
    return {
        f"docs/suspicions/{context.suspicion_id}.yaml": _yaml(yaml_payload),
        f"docs/suspicions/{context.suspicion_id}.md": _ensure_final_newline(
            _render_work_product_template(
                "suspicion.md",
                {
                    "suspicion_id": context.suspicion_id,
                    "title": context.title,
                },
            )
        ),
    }


def _render_task_markdown(context: TaskTemplateContext) -> str:
    return _render_work_product_template(
        "task.md",
        {
            "task_id": context.task_id,
            "title": context.title,
        },
    )


def _render_requirement_markdown(context: RequirementTemplateContext) -> str:
    return _render_work_product_template(
        "requirement.md",
        {
            "requirement_id": context.requirement_id,
            "title": context.title,
        },
    )


def _render_evidence_markdown(context: EvidenceTemplateContext) -> str:
    return _render_work_product_template(
        "evidence.md",
        {
            "evidence_id": context.evidence_id,
            "task_id": context.task_id,
        },
    )


def _render_work_product_template(template_name: str, values: dict[str, str]) -> str:
    template = _read_work_product_template(template_name)
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    unresolved = sorted(set(re.findall(r"{{\s*[\w_]+\s*}}", rendered)))
    if unresolved:
        raise TemplateError(f"未解析的模板变量：{', '.join(unresolved)}")
    return rendered.rstrip()


def _read_work_product_template(template_name: str) -> str:
    source_template = (
        Path(__file__).resolve().parents[2] / "templates" / "work-products" / template_name
    )
    if source_template.exists():
        return source_template.read_text(encoding="utf-8")
    try:
        return (
            resources.files("codex_workbench")
            .joinpath("template_files", "work-products", template_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise TemplateError(f"缺少工作产物模板：{template_name}") from exc


def _knowledge_payload(context: RequirementTemplateContext) -> dict[str, list[str]]:
    payload = {
        "confirmed_facts": _list(context.confirmed_facts),
        "system_observations": _list(context.system_observations),
        "ai_inferences": _list(context.ai_inferences),
        "assumptions": _list(context.assumptions),
        "questions_for_user": _list(context.questions_for_user),
    }
    return {key: value for key, value in payload.items() if value}


def _yaml(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _ensure_final_newline(content: str) -> str:
    return content if content.endswith("\n") else content + "\n"
