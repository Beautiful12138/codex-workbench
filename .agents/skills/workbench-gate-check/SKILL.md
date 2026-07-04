---
name: workbench-gate-check
description: Use when Codex 需要在 codex-workbench 中做阶段推进前自检、运行 task check、判断能否 set-stage 到 in_progress/verification_pending/done/blocked/obsolete，或决定应推进、补资料还是暂停确认。
---

# Workbench Gate Check

## 适用场景

使用本 skill 处理：

- 准备运行 `task check --to ...`。
- 准备运行 `task set-stage --stage ...`。
- 判断 task 能不能进入 `in_progress`、`verification_pending` 或 `done`。
- 判断 task 应该 `blocked`、`obsolete` 还是继续推进。
- 用户问“能不能继续”“能不能完成”“下一步是不是推进阶段”。

## 核心原则

gate-check 是只读自检，不写状态。它不是让 Codex 停下来写长报告，而是在真正推进阶段前确认：事实够不够、风险清不清、验证和交接是否闭环。

gate-check 结果不能作为交付 evidence；它只能说明门禁预演或阻塞诊断发现了什么，不能替代任务本身的交付验证事实。

`task check --to <stage>` 是 CLI 的只读门禁预演，也是底层门禁命令；`task set-stage --stage <stage>` 才会写状态。预演失败时不要绕过 lifecycle guard，也不要用口头判断替代缺失资料。

generated views 只能帮助定位。真正判断阶段、范围、风险、验证和交接时，以 task YAML、task Markdown、evidence、validation、handoff、用户确认和命令输出为准。

## 读取顺序

1. 用 `workspace context` 或用户指向确认工作对象。
2. 先用 `task context <任务名或ID>` 看当前缺口。
3. 需要阶段写入时，再读目标 task 的 `task.yaml`、`task.md` 和 `docs/policies/state-and-gates.md`。
4. 涉及风险、unknown、高风险或真实后果时，读 `docs/policies/risk-and-process.md`。
5. 涉及 done 时，读 evidence、validation、handoff，并按需读 `workbench-evidence`。
6. 涉及环境、数据、权限、部署或外部系统时，读 `workbench-environment` 和相关 `environments/` Markdown。
7. 若要执行 CLI，读 `workbench-cli` 并用 `--help` 核对命令。

若 `task context` 显示 `service_check_limited`，只读分析可继续；进入实现或判断可改代码前，应使用 `--service-check-limit` 扩大检查范围，或点名 `service context <服务名>` 检查本次会触及的服务。

## 入口判断

先判断用户要推进到哪里：

| 目标 | 重点检查 |
| --- | --- |
| `ready` | requirement 是否 readable，目标和完成口径是否清楚 |
| `in_progress` | 是否 implementation-ready，working_scope、risk_triggers、必要复核、验证和回滚是否清楚 |
| `verification_pending` | 实现是否已完成，是否准备记录真实验证 |
| `done` | 是否有 evidence、validation passed、handoff 不等待不拒绝，accepted 有 note |
| `blocked` | 是否有 reason、blocked_by、resume_condition、resume_stage |
| `obsolete` | 是否误建或废弃，是否有 obsolete_reason，是否不应伪装 done |

## in_progress 自检

进入 `in_progress` 前确认：

- task 属于明确 requirement，且 requirement readable。
- 当前请求仍在 task 目标、范围和非范围内。
- `implementation.ready=true`，`implementation.conclusion=scoped`。
- `working_scope` 有真实内容，不是空泛句子。
- 验证方式和回滚思路清楚。
- `risk_triggers` 覆盖需要暂停确认的情况。
- `service_refs` 只是上下文标记，不是修改白名单。
- `impact_profile` 与 `risk_level` / `process_level` 一致。
- high/critical，或经 risk policy 判定需要独立复核的真实后果任务，有 independent review done、implementation ref 和风险接受；复核主体优先子代理。

缺任何关键项时，不要推进到 `in_progress`。先补 `task prepare`、`task impact-set`、子代理复核 / implementation，或暂停确认。

## done 自检

进入 `done` 前确认：

- validation status 是 `passed`。
- validation 有 `evidence_ref`。
- evidence 真实存在且属于当前 task。
- evidence 记录的是已经发生的验证事实，不是计划、推断、doctor clean 或 action note。
- evidence 无未验证项；如果有未验证项，不能按 passed/done 推进。
- handoff 不处于 `waiting_user_validation` 或 `rejected`。
- accepted handoff 有 note；无需用户验收时 handoff 可为 `not_required`。

缺 evidence、validation 或 handoff 时，先读 `workbench-evidence`，不要直接 set-stage done。

## 风险自检

不要因为任务看起来小就跳过风险判断。至少检查：

- `environment` 是否 unknown。
- `data_effect` 是否涉及真实数据、schema 或 destructive。
- `external_effect` 是否写外部系统、部署、通知、费用或安全。
- `blast_radius` 是否影响多服务、共享用户或外部用户。
- `reversibility` 是否 hard、irreversible 或 unknown。
- `contract_change` 是否 true/unknown。
- `security_or_permission` 是否 true/unknown。
- `verification_confidence` 是否 unclear。

任何一项不清，且继续会写状态、改文件或得出完成结论时，暂停确认或补齐 `impact_profile`。

## blocked / obsolete 自检

标记 `blocked` 前确认：原因具体、阻塞方明确、恢复条件可执行、恢复后阶段明确。

标记 `obsolete` 前确认：任务确实误建、重复、被替代或不再需要；它不是为了逃避验证失败或未完成工作；有清楚 obsolete_reason。

## CLI 顺序

只读预演：

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench task check <TASK-ID> --to in_progress
python -m codex_workbench task check <TASK-ID> --to done
```

写入阶段前，再次确认用户授权和门禁结果：

```powershell
python -m codex_workbench task set-stage <TASK-ID> --stage in_progress
python -m codex_workbench task set-stage <TASK-ID> --stage done
```

## 输出建议

向用户汇报时简洁聚焦：

- 能推进：说明依据和即将执行的 CLI。
- 不能推进：列 1-3 个缺口和下一步补法。
- 风险不清：说明哪项 impact_profile 不清，为什么需要确认。
- done 不成立：指出缺少哪个 evidence / validation / handoff。

不要把 gate-check 写成完整审查报告，除非用户明确要求。
