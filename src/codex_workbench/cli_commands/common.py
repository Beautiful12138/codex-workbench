from __future__ import annotations

from pathlib import Path

import typer

from ..doctor import DoctorFinding
from ..errors import WorkbenchError
from ..index import generate_index_views

MARKDOWN_TEMPLATE_HINT = (
    "markdown_template_hint: Markdown 模板只是起稿骨架，用来稍微统一格式；"
    "标题、章节和表达方式可按当前任务自由删改。"
)

MARKDOWN_FOLLOWUP_REQUIRED = (
    "markdown_followup_required: CLI 实际创建 YAML 和 Markdown 后，"
    "除非用户明确只要骨架，Codex 必须在同一轮根据真实现场补写 Markdown；"
    "不得机械复述 YAML，空骨架不算完成。"
)

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
    require_action: bool = True,
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
    if require_action and (not action or not action.strip()):
        raise ValueError("impact_profile_requires_action")

    if require_action:
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

    profile: dict[str, object] = {}
    if action and action.strip():
        profile["action"] = action.strip()
    cleaned_components = [item.strip() for item in components if item.strip()]
    if cleaned_components:
        profile["component_signals"] = cleaned_components
    if environment is not None:
        profile["environment"] = environment.strip()
    if data_effect is not None:
        profile["data_effect"] = data_effect.strip()
    if external_effect is not None:
        profile["external_effect"] = external_effect.strip()
    if blast_radius is not None:
        profile["blast_radius"] = blast_radius.strip()
    if reversibility is not None:
        profile["reversibility"] = reversibility.strip()
    if contract_change is not None:
        profile["contract_change"] = _parse_impact_truth(contract_change)
    if security_or_permission is not None:
        profile["security_or_permission"] = _parse_impact_truth(security_or_permission)
    if verification_confidence is not None:
        profile["verification_confidence"] = verification_confidence.strip()
    return profile

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
    typer.echo(MARKDOWN_FOLLOWUP_REQUIRED)

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
