from __future__ import annotations

from pydantic import BaseModel

from .models import (
    CURRENT_SCHEMA_VERSION as CURRENT_SCHEMA_VERSION,
    ActionNoteState,
    ArchiveEntryState,
    ArchiveManifestState,
    ChangeRecordState,
    DecisionState,
    DiscoveryState,
    EvidenceState,
    MaterialRegistry,
    RequirementState,
    ServiceRegistry,
    SuspicionState,
    TaskState,
    WorkspaceState,
)


CORE_MODEL_TYPES: tuple[type[BaseModel], ...] = (
    WorkspaceState,
    RequirementState,
    TaskState,
    MaterialRegistry,
    DiscoveryState,
    ServiceRegistry,
    EvidenceState,
    ActionNoteState,
    ChangeRecordState,
    DecisionState,
    SuspicionState,
    ArchiveEntryState,
    ArchiveManifestState,
)


def core_model_json_schemas() -> dict[str, dict[str, object]]:
    return {model_type.__name__: model_type.model_json_schema() for model_type in CORE_MODEL_TYPES}
