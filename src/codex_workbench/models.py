from __future__ import annotations

from enum import Enum
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CURRENT_SCHEMA_VERSION = "0.1"
SchemaVersion = Literal["0.1"]
NonEmptyString = Annotated[str, Field(min_length=1)]
REQUIREMENT_ID_PATTERN = re.compile(r"^REQ-\d{8}-\d{3,}$")
TASK_ID_PATTERN = re.compile(r"^(REQ-\d{8}-\d{3,})-TASK-\d{8}-\d{3,}$")


class WorkbenchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkspaceStatus(str, Enum):
    BASELINE = "baseline"
    REQUIREMENT = "requirement"


class TaskStage(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    VERIFICATION_PENDING = "verification_pending"
    BLOCKED = "blocked"
    DONE = "done"
    OBSOLETE = "obsolete"


class ProcessLevel(str, Enum):
    MICRO = "micro"
    LIGHTWEIGHT = "lightweight"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class RequirementReadinessStatus(str, Enum):
    RAW_MATERIALS = "raw_materials"
    DISCOVERY = "discovery"
    INTAKE_DRAFT = "intake_draft"
    NEEDS_CONFIRMATION = "needs_confirmation"
    READABLE = "readable"


class ReadinessConclusion(str, Enum):
    SCOPED = "scoped"
    NEEDS_CHANGES = "needs_changes"
    BLOCKED = "blocked"


class ReviewStatus(str, Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    DONE = "done"
    NEEDS_CHANGES = "needs_changes"
    BLOCKED = "blocked"


class ValidationStatus(str, Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    CLOSED_WITH_EXCEPTION = "closed_with_exception"


class HandoffStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    WAITING_USER_VALIDATION = "waiting_user_validation"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class BlockedBy(str, Enum):
    USER = "user"
    ENVIRONMENT = "environment"
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    EXTERNAL_SERVICE = "external_service"
    QA = "qa"
    PRODUCT = "product"
    OTHER = "other"


class ConfirmationType(str, Enum):
    SCOPE_CONFIRMATION = "scope_confirmation"
    EXECUTION_AUTHORIZATION = "execution_authorization"
    RISK_ACCEPTANCE = "risk_acceptance"
    ENVIRONMENT_OPERATION_AUTHORIZATION = "environment_operation_authorization"
    ACCEPTANCE_CONFIRMATION = "acceptance_confirmation"
    REQUIREMENT_CLOSURE = "requirement_closure"
    ARCHIVE_AUTHORIZATION = "archive_authorization"


class ChangeKind(str, Enum):
    IMPLEMENTATION_ADJUSTMENT = "implementation_adjustment"
    SCOPE_CLARIFICATION = "scope_clarification"
    SCOPE_CHANGE = "scope_change"


class ActionType(str, Enum):
    MAINTENANCE_ACTION = "maintenance_action"
    OPS_ACTION = "ops_action"
    EPHEMERAL_CHECK = "ephemeral_check"


class ActionStatus(str, Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    PARTIAL = "partial"
    FAILED = "failed"
    REVERTED = "reverted"


class Knowledge(WorkbenchModel):
    confirmed_facts: list[str] = Field(default_factory=list)
    system_observations: list[str] = Field(default_factory=list)
    ai_inferences: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions_for_user: list[str] = Field(default_factory=list)


class RequirementReadinessState(WorkbenchModel):
    status: RequirementReadinessStatus = RequirementReadinessStatus.RAW_MATERIALS
    confirmed_by_user: bool = False
    material_refs: list[str] = Field(default_factory=list)
    discovery_refs: list[str] = Field(default_factory=list)


class MaterialEntry(WorkbenchModel):
    id: NonEmptyString
    title: NonEmptyString
    source: NonEmptyString
    received_at: NonEmptyString
    summary: NonEmptyString
    sensitivity: str = "low"
    large_file: bool = False
    original_location: str | None = None
    committable_original: bool = False
    related_refs: list[str] = Field(default_factory=list)
    retention: str | None = None


class MaterialRegistry(WorkbenchModel):
    schema_version: SchemaVersion
    materials: list[MaterialEntry] = Field(default_factory=list)


class DiscoveryState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    material_refs: list[str] = Field(default_factory=list)
    updated_at: NonEmptyString
    knowledge: Knowledge = Field(default_factory=Knowledge)


class ReviewState(WorkbenchModel):
    status: ReviewStatus = ReviewStatus.NOT_STARTED
    ref: str | None = None


class ImplementationState(WorkbenchModel):
    ready: bool = False
    conclusion: ReadinessConclusion | None = None
    ref: str | None = None


class ValidationState(WorkbenchModel):
    status: ValidationStatus = ValidationStatus.NOT_STARTED
    evidence_ref: str | None = None
    unverified_items: list[str] = Field(default_factory=list)


class HandoffState(WorkbenchModel):
    status: HandoffStatus = HandoffStatus.NOT_REQUIRED
    note: str | None = None


class BlockedState(WorkbenchModel):
    reason: str | None = None
    blocked_by: BlockedBy | None = None
    resume_condition: str | None = None
    resume_stage: TaskStage | None = None


class ConfirmationState(WorkbenchModel):
    type: ConfirmationType
    source: str = "user"
    note: str | None = None


class WorkspaceState(WorkbenchModel):
    schema_version: SchemaVersion
    workspace_status: WorkspaceStatus = WorkspaceStatus.BASELINE
    service_registry: str = "services/registry.yaml"
    active_packages: str = "docs/active/"
    generated_views: str = "docs/generated/"


class RequirementState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    goal: NonEmptyString
    created_at: NonEmptyString
    updated_at: NonEmptyString
    readiness: RequirementReadinessState = Field(default_factory=RequirementReadinessState)
    non_goals: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)
    task_refs: list[str] = Field(default_factory=list)
    knowledge: Knowledge = Field(default_factory=Knowledge)
    confirmations: list[ConfirmationState] = Field(default_factory=list)

    @field_validator("id")
    def require_dated_requirement_id(cls, value: str) -> str:
        if not REQUIREMENT_ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid_requirement_id_format: {value}")
        return value


class TaskState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    requirement_id: NonEmptyString
    title: NonEmptyString
    created_at: NonEmptyString
    updated_at: NonEmptyString
    stage: TaskStage = TaskStage.DRAFT
    next_step: NonEmptyString | None = None
    process_level: ProcessLevel = ProcessLevel.MICRO
    risk_level: RiskLevel = RiskLevel.LOW
    service_refs: list[str] = Field(default_factory=list)
    knowledge: Knowledge = Field(default_factory=Knowledge)
    review: ReviewState = Field(default_factory=ReviewState)
    implementation: ImplementationState = Field(default_factory=ImplementationState)
    validation: ValidationState = Field(default_factory=ValidationState)
    handoff: HandoffState = Field(default_factory=HandoffState)
    blocked: BlockedState | None = None
    obsolete_reason: str | None = None
    confirmations: list[ConfirmationState] = Field(default_factory=list)
    working_scope: list[str] = Field(default_factory=list)
    likely_touchpoints: list[str] = Field(default_factory=list)
    risk_triggers: list[str] = Field(default_factory=list)

    @field_validator("requirement_id")
    def require_dated_requirement_ref(cls, value: str) -> str:
        if not REQUIREMENT_ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid_requirement_id_format: {value}")
        return value

    @model_validator(mode="after")
    def require_requirement_prefixed_id(self) -> "TaskState":
        expected_prefix = f"{self.requirement_id}-"
        if not self.id.startswith(expected_prefix):
            raise ValueError(
                f"task_id_requirement_prefix_mismatch: {self.requirement_id} -> {self.id}"
            )
        match = TASK_ID_PATTERN.fullmatch(self.id)
        if not match or match.group(1) != self.requirement_id:
            raise ValueError(f"invalid_task_id_format: {self.id}")
        return self


class ServiceEntry(WorkbenchModel):
    name: NonEmptyString
    local_path: str | None = None
    purpose: str | None = None
    notes: str | None = None


class ServiceRegistry(WorkbenchModel):
    schema_version: SchemaVersion
    services: list[ServiceEntry] = Field(default_factory=list)
    notes: str | None = None


class EvidenceState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    task_id: NonEmptyString
    conclusion: ValidationStatus
    key_outputs: list[str] = Field(default_factory=list)
    unverified_items: list[str] = Field(default_factory=list)
    knowledge: Knowledge = Field(default_factory=Knowledge)


class ActionNoteState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    updated_at: NonEmptyString
    summary: NonEmptyString
    action_type: ActionType
    status: ActionStatus = ActionStatus.EXECUTED
    authorization: str | None = None
    target: str | None = None
    result: str | None = None
    related_refs: list[str] = Field(default_factory=list)
    side_effect_summary: NonEmptyString
    rollback_hint: NonEmptyString


class ChangeRecordState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    updated_at: NonEmptyString
    change_kind: ChangeKind = ChangeKind.SCOPE_CHANGE
    changed_area: NonEmptyString
    reason: NonEmptyString
    impact: NonEmptyString
    handling: NonEmptyString
    related_refs: list[str] = Field(default_factory=list)

    @field_validator("change_kind")
    @classmethod
    def require_scope_change(cls, value: ChangeKind) -> ChangeKind:
        if value is not ChangeKind.SCOPE_CHANGE:
            raise ValueError("formal_change_record_requires_scope_change")
        return value


class DecisionState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    updated_at: NonEmptyString
    cold_path_reason: NonEmptyString
    status: str = "active"
    context: NonEmptyString
    decision: NonEmptyString
    impact: NonEmptyString


class SuspicionState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    title: NonEmptyString
    updated_at: NonEmptyString
    location_or_subject: NonEmptyString
    confirmed_facts: list[NonEmptyString] = Field(min_length=1)
    ai_inferences: list[NonEmptyString] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    current_task_impact: NonEmptyString
    suggested_handling: NonEmptyString
    related_refs: list[str] = Field(default_factory=list)


class ArchiveEntryState(WorkbenchModel):
    schema_version: SchemaVersion
    id: NonEmptyString
    version: NonEmptyString
    source_kind: NonEmptyString
    source_id: NonEmptyString
    source_path: NonEmptyString
    archive_path: NonEmptyString
    reason: str = ""
    archived_at: str | None = None
    preflight_summary: list[str] = Field(default_factory=list)


class ArchiveManifestState(WorkbenchModel):
    schema_version: SchemaVersion
    version: NonEmptyString
    archived_at: NonEmptyString
    authorization: ConfirmationState
    requirement_ids: list[NonEmptyString] = Field(default_factory=list)
    entries: list[ArchiveEntryState] = Field(default_factory=list)

    @field_validator("authorization")
    @classmethod
    def require_archive_authorization(cls, value: ConfirmationState) -> ConfirmationState:
        if value.type is not ConfirmationType.ARCHIVE_AUTHORIZATION:
            raise ValueError("archive_manifest_requires_archive_authorization")
        return value
