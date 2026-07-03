from __future__ import annotations

from codex_workbench.advice import task_command_advice_lines, workspace_advice_lines


def test_workspace_advice_routes_baseline_to_lightweight_entry_choices() -> None:
    lines = workspace_advice_lines(
        active_requirement_count=0,
        active_task_count=0,
        has_conflicts=False,
        has_waiting_feedback=False,
        has_blocked=False,
        has_needs_confirmation=False,
    )

    joined = "\n".join(lines)
    assert "不写状态" in joined
    assert "material / discovery / intake" in joined
    assert "maintenance_action" in joined


def test_workspace_advice_distinguishes_active_requirement_without_task() -> None:
    lines = workspace_advice_lines(
        active_requirement_count=1,
        active_task_count=0,
        has_conflicts=False,
        has_waiting_feedback=False,
        has_blocked=False,
        has_needs_confirmation=False,
    )

    joined = "\n".join(lines)
    assert "已有活动需求" in joined
    assert "创建或选择 task" in joined
    assert "要纳入新需求" not in joined


def test_workspace_advice_routes_active_workspace_to_context_and_checks() -> None:
    lines = workspace_advice_lines(
        active_requirement_count=1,
        active_task_count=2,
        has_conflicts=True,
        has_waiting_feedback=True,
        has_blocked=True,
        has_needs_confirmation=True,
    )

    joined = "\n".join(lines)
    assert "task context <任务名或ID>" in joined
    assert "index check" in joined
    assert "doctor check" in joined
    assert "evidence / validation / handoff" in joined
    assert "task check <task-id> --to in_progress" in joined
    assert "task impact-set" in joined


def test_task_command_advice_maps_gate_reasons_to_cli_commands() -> None:
    lines = task_command_advice_lines(
        code_change_state="blocked",
        code_change_gaps=(
            "missing_implementation_ready",
            "unknown_service_ref:web",
            "impact_profile_requires_risk_escalation",
        ),
        claim_done_state="blocked",
        claim_done_gaps=("missing_evidence", "handoff_waiting"),
    )

    joined = "\n".join(lines)
    assert "task prepare <task-id>" in joined
    assert "service add <name>" in joined
    assert "task impact-set <task-id>" in joined
    assert "evidence create" in joined
    assert "validation apply" in joined
    assert "handoff set <task-id>" in joined
    assert "REQ-" not in joined


def test_task_command_advice_handles_ready_stage_updates() -> None:
    lines = task_command_advice_lines(
        code_change_state="after_stage_update",
        code_change_gaps=("task_not_in_progress",),
        claim_done_state="ready_to_mark_done",
        claim_done_gaps=(),
    )

    joined = "\n".join(lines)
    assert "task check <task-id> --to in_progress" in joined
    assert "task set-stage <task-id> --stage in_progress" in joined
    assert "task check <task-id> --to done" in joined
    assert "task set-stage <task-id> --stage done" in joined


def test_task_command_advice_includes_required_prepare_arguments() -> None:
    lines = task_command_advice_lines(
        code_change_state="blocked",
        code_change_gaps=(
            "missing_high_risk_review",
            "missing_high_risk_implementation_ref",
        ),
        claim_done_state="blocked",
        claim_done_gaps=(),
    )

    joined = "\n".join(lines)
    assert "task prepare <task-id> --working-scope <scope> --review-ref review.md" in joined
    assert "task prepare <task-id> --working-scope <scope> --implementation-ref implementation.md" in joined


def test_task_command_advice_does_not_confuse_review_reason_prefixes() -> None:
    lines = task_command_advice_lines(
        code_change_state="blocked",
        code_change_gaps=(
            "missing_high_risk_review_reviewer",
            "missing_high_risk_independent_review",
        ),
        claim_done_state="blocked",
        claim_done_gaps=(),
    )

    joined = "\n".join(lines)
    assert "task review-create" not in joined
    assert "--reviewer subagent --review-independent" in joined


def test_task_command_advice_keeps_validation_status_conservative() -> None:
    lines = task_command_advice_lines(
        code_change_state="allowed",
        code_change_gaps=(),
        claim_done_state="blocked",
        claim_done_gaps=(
            "missing_evidence",
            "validation_not_passed",
            "evidence_ref_mismatch: expected=EV-1 actual=EV-2",
        ),
    )

    joined = "\n".join(lines)
    assert "validation apply <task-id> --evidence-id <evidence-id> --status <status>" in joined
    assert "不能直接标记 passed" in joined
    assert "validation.evidence_ref" in joined
    assert "--status passed" not in joined
