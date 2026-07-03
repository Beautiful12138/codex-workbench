# 生命周期语义

本文件是冷路径策略说明，用来支撑 CLI、doctor 和测试；不要把它复制进 `AGENTS.md` 或 hook 热路径。

## 主阶段

`task.yaml` 的主阶段保持少量枚举：

```text
draft | ready | in_progress | verification_pending | blocked | done | obsolete
```

`review`、`implementation`、`validation`、`handoff`、`blocked`、`process_level` 和 `risk_level` 是状态维度，不是额外主阶段。

## 转移 guard

- 进入 `in_progress` 前必须有 implementation-ready：`implementation.ready=true` 且 `implementation.conclusion=scoped`；最小状态用 `task prepare` 写入。
- `task check --to <stage>` 只读预演同一套门禁；真正写阶段仍使用 `task set-stage`。
- `risk_level=high|critical` 或 `process_level=high|critical` 进入 `in_progress` 前，还需要 `review.status=done`、`review.independent=true`、`review.reviewer`、`implementation.ref`、`working_scope`、`risk_triggers` 和 `risk_acceptance` confirmation；复核主体优先使用子代理。
- `risk_triggers` 是暂停确认条件，不是路径白名单；触发后先对齐目标、风险或授权。
- `service_refs` 是相关服务标记，用于恢复上下文和状态展示；它不是文件路径白名单，但写出的 service ref 必须能对应已登记服务。
- 进入 `done` 前必须有 `validation.status=passed`、`validation.evidence_ref`、无未验证项，并且 handoff 不处于等待或拒绝状态。
- `blocked` 必须说明原因、阻塞方、恢复条件和恢复后阶段。
- `obsolete` 必须有废弃原因；它只表示误建或废弃，不替代 done、validation 或 handoff。
- 归档只能处理已闭环或废弃任务；`handoff.waiting_user_validation` 不能归档。

## 轻量路径

`process_level` 只控制显性化强度，不降低安全语义。`micro` 和 `lightweight` 可以少文件、少仪式，但不能跳过目标、范围、验证、交接和完成 guard。

风险按真实后果判断，不按组件名判断。`impact_profile` 用于说明 `risk_level` / `process_level` 的依据；当画像显示真实数据、生产/共享环境、权限安全、部署、不可逆、影响他人、契约变化或验证/回滚不清时，不能按 low/micro 推进。完整规则见 `docs/policies/risk-and-process.md`。

## requirement readiness

正式任务必须来自可读需求：`requirement.readiness.status=readable` 且 `confirmed_by_user=true`。原始材料、discovery、intake draft 和待确认状态都不能直接授权正式开发。

低风险 micro 任务可以使用任务包内的最小 Requirement Snapshot，但这个快照只支撑当前任务，不能替代整个需求包成熟度。

## 冲突裁决

状态冲突不能按更新时间静默覆盖。以下是事实证据层级，不改变 YAML 是机器状态真源：

```text
live_evidence
> evidence
> action_note
> requirement
> discovery
> generated_index
> task_yaml_next_step
> ai_inference
> assumption
```

较低层级不能覆盖较高层级。无法裁决时保持保守状态，报告冲突，等待用户确认或进入变更控制。

## 事实和证据

Evidence 记录任务验证事实；Action Note 只记录非任务动作。Action Note 的 `status`、授权、目标和结果只是动作上下文，不能替代 task evidence，也不能支撑 `validation.status=passed`。

工具输出只能证明事实，不自动证明用户验收、风险接受或任务完成。

## 任务第一屏

`task.md` 第一屏保留“用户目标”、“完成口径”、“范围”、“实现提示”、“验证要求”和“备注”等起稿标题，正文由 AI 按当前任务填写。`task.yaml.next_step` 是恢复提示；生命周期细节通过 YAML、CLI、doctor 和冷路径 policy 呈现，不抢占任务心智。
