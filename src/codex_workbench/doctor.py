from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ValidationError

from .index import check_generated_views
from .lifecycle import evaluate_archive_task, evaluate_task_transition
from .models import (
    ActionNoteState,
    ArchiveManifestState,
    ChangeRecordState,
    DecisionState,
    DiscoveryState,
    EvidenceState,
    MaterialRegistry,
    ServiceRegistry,
    SuspicionState,
    TaskStage,
    TaskState,
    RequirementState,
)
from .validation import assert_done_evidence_valid


@dataclass(frozen=True)
class DoctorFinding:
    severity: str
    code: str
    message: str
    path: str | None = None
    subject: str | None = None


@dataclass(frozen=True)
class DoctorReport:
    findings: tuple[DoctorFinding, ...]

    @property
    def blockings(self) -> tuple[DoctorFinding, ...]:
        return tuple(finding for finding in self.findings if finding.severity == "blocking")

    @property
    def warnings(self) -> tuple[DoctorFinding, ...]:
        return tuple(finding for finding in self.findings if finding.severity == "warning")

    @property
    def suggestions(self) -> tuple[DoctorFinding, ...]:
        return tuple(finding for finding in self.findings if finding.severity == "suggestion")

    @property
    def clean(self) -> bool:
        return not self.blockings


@dataclass(frozen=True)
class _ModelRecord:
    path: Path
    relative_path: str
    model: BaseModel


def run_doctor(workspace_root: str | Path) -> DoctorReport:
    root = Path(workspace_root).expanduser().resolve()
    findings: list[DoctorFinding] = []
    task_records: list[_ModelRecord] = []

    for model_spec in _model_specs():
        records, model_findings = _read_model_records(root, model_spec.pattern, model_spec.model_type)
        findings.extend(model_findings)
        if model_spec.model_type is TaskState:
            task_records.extend(records)

    findings.extend(_index_findings(root))
    for record in task_records:
        findings.extend(_task_gate_findings(root, record))

    return DoctorReport(findings=tuple(_dedupe_findings(findings)))


@dataclass(frozen=True)
class _ModelSpec:
    pattern: str
    model_type: type[BaseModel]


def _model_specs() -> tuple[_ModelSpec, ...]:
    return (
        _ModelSpec("services/registry.yaml", ServiceRegistry),
        _ModelSpec("docs/inbox/materials.yaml", MaterialRegistry),
        _ModelSpec("docs/inbox/*/discovery.yaml", DiscoveryState),
        _ModelSpec("docs/active/*/requirement.yaml", RequirementState),
        _ModelSpec("docs/active/*/task.yaml", TaskState),
        _ModelSpec("docs/active/*/evidence.yaml", EvidenceState),
        _ModelSpec("docs/archive/*/archive.yaml", ArchiveManifestState),
        _ModelSpec("docs/actions/*.yaml", ActionNoteState),
        _ModelSpec("docs/changes/*.yaml", ChangeRecordState),
        _ModelSpec("docs/decisions/*.yaml", DecisionState),
        _ModelSpec("docs/suspicions/*.yaml", SuspicionState),
    )


def _read_model_records(
    root: Path,
    pattern: str,
    model_type: type[BaseModel],
) -> tuple[list[_ModelRecord], list[DoctorFinding]]:
    records: list[_ModelRecord] = []
    findings: list[DoctorFinding] = []
    for path in sorted(root.glob(pattern), key=lambda item: item.as_posix()):
        relative_path = path.relative_to(root).as_posix()
        try:
            data = _load_yaml_dict(path)
            model = model_type.model_validate(data)
        except yaml.YAMLError as exc:
            findings.append(
                _blocking(
                    "invalid_yaml",
                    f"{relative_path} YAML 无法解析：{exc.__class__.__name__}",
                    path=relative_path,
                )
            )
            continue
        except ValidationError as exc:
            findings.append(
                _blocking(
                    "invalid_model",
                    f"{relative_path} 不符合 {model_type.__name__}：{_validation_summary(exc)}",
                    path=relative_path,
                )
            )
            continue
        records.append(_ModelRecord(path=path, relative_path=relative_path, model=model))
    return records, findings


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise yaml.YAMLError("top_level_yaml_must_be_mapping")
    return data


def _validation_summary(exc: ValidationError) -> str:
    if not exc.errors():
        return "validation_error"
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ())) or "<root>"
    message = str(first.get("msg", "validation_error"))
    return f"{location}: {message}"


def _index_findings(root: Path) -> list[DoctorFinding]:
    result = check_generated_views(root)
    findings: list[DoctorFinding] = []
    for conflict in result.conflicts:
        findings.append(_blocking(_code_from_conflict(conflict), conflict))
    for message in result.messages:
        if message.startswith("conflict: "):
            continue
        code = "generated_view_missing" if message.startswith("missing: ") else "generated_view_stale"
        findings.append(_warning(code, _generated_view_message(message), path=_path_from_index_message(message)))
    return findings


def _task_gate_findings(root: Path, record: _ModelRecord) -> list[DoctorFinding]:
    task = record.model
    if not isinstance(task, TaskState):
        return []

    findings: list[DoctorFinding] = []
    if task.validation.status.value == "passed" and not task.validation.evidence_ref:
        findings.append(
            _blocking(
                "validation_passed_without_evidence",
                f"{task.id} validation 已通过但缺少 evidence_ref",
                path=record.relative_path,
                subject=task.id,
            )
        )
    if task.validation.status.value == "passed" and task.validation.unverified_items:
        findings.append(
            _blocking(
                "validation_passed_with_unverified_items",
                f"{task.id} validation 已通过但仍有未验证项",
                path=record.relative_path,
                subject=task.id,
            )
        )
    if task.validation.evidence_ref and (
        task.stage is TaskStage.DONE or task.validation.status.value == "passed"
    ):
        try:
            assert_done_evidence_valid(root, task)
        except Exception as exc:  # noqa: BLE001 - Doctor converts checker failures into findings.
            findings.append(
                _blocking(
                    _reason_code(str(exc)),
                    f"{task.id} evidence 校验失败：{exc}",
                    path=record.relative_path,
                    subject=task.id,
                )
            )

    if task.stage is TaskStage.DONE:
        findings.extend(_transition_findings(record, task, TaskStage.DONE, "done_gate_blocked"))
        findings.extend(_archive_findings(record, task))
    if task.stage is TaskStage.IN_PROGRESS:
        findings.extend(
            _transition_findings(record, task, TaskStage.IN_PROGRESS, "in_progress_gate_blocked")
        )
    if task.stage is TaskStage.BLOCKED:
        findings.extend(_transition_findings(record, task, TaskStage.BLOCKED, "blocked_state_invalid"))
    if task.stage is TaskStage.OBSOLETE:
        findings.extend(_transition_findings(record, task, TaskStage.OBSOLETE, "obsolete_state_invalid"))
    return findings


def _transition_findings(
    record: _ModelRecord,
    task: TaskState,
    target: TaskStage,
    code: str,
) -> list[DoctorFinding]:
    check = evaluate_task_transition(task, target)
    if check.allowed:
        return []
    reasons = ", ".join(check.reason_codes)
    return [
        _blocking(
            code,
            f"{task.id} 阶段门未通过：{reasons}",
            path=record.relative_path,
            subject=task.id,
        )
    ]


def _archive_findings(record: _ModelRecord, task: TaskState) -> list[DoctorFinding]:
    check = evaluate_archive_task(task)
    if check.allowed:
        return []
    reasons = ", ".join(check.reason_codes)
    return [
        _blocking(
            "archive_preflight_blocked",
            f"{task.id} 归档前置检查未通过：{reasons}",
            path=record.relative_path,
            subject=task.id,
        )
    ]


def _generated_view_message(message: str) -> str:
    if message.startswith("missing: "):
        return f"{message.removeprefix('missing: ')} 缺失"
    if message.startswith("stale: "):
        return f"{message.removeprefix('stale: ')} 已过期"
    return message


def _path_from_index_message(message: str) -> str | None:
    if ": " not in message:
        return None
    return message.split(": ", 1)[1]


def _code_from_conflict(conflict: str) -> str:
    return _reason_code(conflict.split(":", 1)[0])


def _reason_code(value: str) -> str:
    raw = value.split(":", 1)[0].strip().lower()
    return "".join(char if char.isalnum() or char == "_" else "_" for char in raw) or "doctor_check_failed"


def _blocking(
    code: str,
    message: str,
    *,
    path: str | None = None,
    subject: str | None = None,
) -> DoctorFinding:
    return DoctorFinding("blocking", code, message, path=path, subject=subject)


def _warning(
    code: str,
    message: str,
    *,
    path: str | None = None,
    subject: str | None = None,
) -> DoctorFinding:
    return DoctorFinding("warning", code, message, path=path, subject=subject)


def _dedupe_findings(findings: Iterable[DoctorFinding]) -> list[DoctorFinding]:
    seen: set[tuple[str, str, str, str | None, str | None]] = set()
    deduped: list[DoctorFinding] = []
    for finding in findings:
        key = (finding.severity, finding.code, finding.message, finding.path, finding.subject)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped
