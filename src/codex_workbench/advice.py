from __future__ import annotations

from collections.abc import Iterable


def workspace_advice_lines(
    *,
    active_requirement_count: int,
    active_task_count: int,
    has_conflicts: bool,
    has_waiting_feedback: bool,
    has_blocked: bool,
    has_needs_confirmation: bool,
) -> tuple[str, ...]:
    if active_task_count == 0:
        if active_requirement_count > 0:
            return (
                "已有活动需求但没有活动任务：先对齐 requirement 包和 index/recovery，不直接推进阶段。",
                "要继续实现：基于已确认 requirement 创建或选择 task；若已闭环，再走 requirement close / archive preflight。",
                "普通讨论或只读探索：直接继续，不写状态。",
            )
        return (
            "普通讨论或只读探索：直接继续，不写状态。",
            "要纳入新需求：先登记 material / discovery / intake，用户确认后再创建 task。",
            "维护本仓库：按 maintenance_action 小修；完成后运行最小验证。",
        )

    lines = ["先运行 `task context <任务名或ID>` 对齐当前任务、服务现场和能力矩阵。"]
    if has_conflicts:
        lines.append("存在冲突：先运行 `index check` / `doctor check`，再处理 YAML 真源问题。")
    if has_waiting_feedback:
        lines.append("等待反馈：拿到测试或用户结果后，再补 evidence / validation / handoff。")
    if has_blocked:
        lines.append(
            "阻塞任务：先用 `task context <任务名或ID>` 对齐恢复条件；"
            "需要接回执行时先 `task check <task-id> --to in_progress`，通过后再 `task set-stage`。"
        )
    if has_needs_confirmation:
        lines.append("需确认任务：先补范围、风险、服务或授权事实，必要时用 task impact-set。")
    return tuple(lines)


def task_command_advice_lines(
    *,
    code_change_state: str,
    code_change_gaps: Iterable[str],
    claim_done_state: str,
    claim_done_gaps: Iterable[str],
    warnings: Iterable[str] = (),
) -> tuple[str, ...]:
    reasons = tuple(dict.fromkeys((*code_change_gaps, *claim_done_gaps, *warnings)))
    lines: list[str] = []

    if claim_done_state == "ready_to_mark_done":
        lines.append("`task check <task-id> --to done` -> `task set-stage <task-id> --stage done`：预演通过后再写入 done。")
    if code_change_state == "after_stage_update" or _has_reason(reasons, "task_not_in_progress"):
        lines.append(
            "`task check <task-id> --to in_progress` -> "
            "`task set-stage <task-id> --stage in_progress`：预演通过后再进入实现态。"
        )
    if _has_reason(reasons, "missing_implementation_ready"):
        lines.append("`task prepare <task-id> --working-scope <scope>`：补 implementation-ready 和工作范围。")
    if _has_reason(reasons, "service_check_limited"):
        lines.append("`task context <任务名或ID> --service-check-limit <N>`：展开未检查服务后再判断能否改代码。")
    if _has_reason(reasons, "unknown_service_ref"):
        lines.append("`service add <name> --path <path>`：登记缺失服务，或调整任务的 service_refs。")
    if any(_has_reason(reasons, item) for item in ("path_missing", "empty_service_dir", "service_path_is_file")):
        lines.append("`service context <service-name>`：先确认服务真实路径和入口文件。")
    if any(
        _has_reason(reasons, item)
        for item in (
            "impact_profile_requires_risk_escalation",
            "impact_profile_requires_process_escalation",
            "impact_profile_unknown_for_micro",
            "missing_high_risk_impact_profile",
        )
    ):
        lines.append("`task impact-set <task-id> ... --reason <reason>`：修正影响面画像、风险等级或流程档位。")
    if _has_reason(reasons, "missing_high_risk_review"):
        lines.append(
            "`task review-create <task-id>`，再用 "
            "`task prepare <task-id> --working-scope <scope> --review-ref review.md "
            "--reviewer subagent --review-independent`。"
        )
    if any(
        _has_reason(reasons, item)
        for item in (
            "missing_high_risk_review_reviewer",
            "missing_high_risk_independent_review",
        )
    ):
        lines.append(
            "`task prepare <task-id> --working-scope <scope> --reviewer subagent "
            "--review-independent`：补复核主体和独立复核声明。"
        )
    if _has_reason(reasons, "missing_high_risk_implementation_ref"):
        lines.append(
            "`task implementation-create <task-id>`，再用 "
            "`task prepare <task-id> --working-scope <scope> --implementation-ref implementation.md`。"
        )
    if any(
        _has_reason(reasons, item)
        for item in (
            "missing_high_risk_working_scope",
            "missing_high_risk_triggers",
            "missing_high_risk_acceptance",
        )
    ):
        lines.append("`task prepare <task-id> ...`：补高风险工作范围、暂停条件和风险接受说明。")
    if any(
        _has_reason(reasons, item)
        for item in (
            "missing_evidence",
            "missing_evidence_record",
        )
    ):
        lines.append(
            "`evidence create <evidence-id> --task-id <task-id> ...` -> "
            "`validation apply <task-id> --evidence-id <evidence-id> --status <status>`：按真实验证结果记录并应用。"
        )
    if any(
        _has_reason(reasons, item)
        for item in (
            "validation_not_passed",
            "evidence_not_passed",
            "evidence_has_unverified_items",
            "unverified_items_present",
        )
    ):
        lines.append("验证未通过或仍有未验证项：先修复或重测并记录真实 evidence，不能直接标记 passed。")
    if any(
        _has_reason(reasons, item)
        for item in (
            "invalid_evidence_record",
            "evidence_ref_mismatch",
            "validation_record_rejected",
            "invalid_evidence_conclusion",
        )
    ):
        lines.append(
            "evidence/ref 不一致或记录无效：先修复 validation.evidence_ref 或重建 evidence，再重新 apply validation。"
        )
    if _has_reason(reasons, "handoff_waiting"):
        lines.append("等待用户或测试反馈后，再运行 `handoff set <task-id> --status accepted --note <note>`。")
    if _has_reason(reasons, "missing_handoff_note"):
        lines.append("`handoff set <task-id> --status accepted --note <note>`：补用户验收说明。")
    if _has_reason(reasons, "handoff_rejected"):
        lines.append("handoff 已拒绝：按反馈继续修复，不能标记 done。")
    if _has_reason(reasons, "requirement_missing_or_invalid"):
        lines.append("先修复 requirement 包或确认任务归属，再继续推进。")

    return tuple(dict.fromkeys(lines))


def _has_reason(reasons: Iterable[str], code: str) -> bool:
    return any(_reason_matches(str(reason), code) for reason in reasons)


def _reason_matches(reason: str, code: str) -> bool:
    return reason == code or reason.startswith(f"{code}:")
