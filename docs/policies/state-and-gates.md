# 状态与门禁

本文件说明 Workbench 的阶段语义和推进条件。机器状态以 YAML 为准，Markdown 只解释现场。

## 需求入口

- 原始聊天、截图、文件、日志和 AI 推断都不是可开发事实。
- `material` 只证明收到过输入，并保存脱敏摘要。
- `discovery` 记录只读探索得到的系统观察、AI 推断、假设和待确认问题。
- `intake` 把材料和 discovery 转成 AI-readable 需求草案。
- 只有 `readiness.status=readable` 且 `confirmed_by_user=true` 后，requirement 才能创建正式 task。

## task 是执行界面

task 包应回答：

- 用户目标是什么。
- 完成口径是什么。
- 当前范围和非范围是什么。
- 涉及哪些服务。
- 下一步是什么。
- 进入实现前的范围、暂停条件、验证和回滚是什么。
- 风险等级和流程档位为什么成立；复杂组件只作为线索，真实后果判断见 `docs/policies/risk-and-process.md`。

`task.yaml.next_step` 是恢复提示，不是完成事实。

## implementation-ready

修改任务目标内文件前，task 必须满足：

- stage 可以推进到 `in_progress`。
- `implementation.ready=true`。
- `implementation.conclusion=scoped`。
- `working_scope` 有真实内容。
- 验证方式和回滚思路清楚。
- 触发真实后果风险时有 `risk_triggers` 和必要确认。

低风险任务可以少文件，但不能跳过这些语义。高风险或 critical 任务进入 `in_progress` 前还需要 review done、implementation ref、working_scope、risk_triggers 和风险接受说明。

如果 task 写有 `impact_profile`，阶段推进时应核对它是否与 `risk_level` / `process_level` 一致。真实数据写入、生产/共享环境、权限安全、部署、不可逆、影响他人、环境不清、授权不清或回滚不清，不能仍按 micro/low 直接推进。

## 阶段推进

- `task check --to <stage>` 只读预演门禁。
- `task set-stage` 才写阶段。
- `blocked` 必须有 reason、blocked_by、resume_condition 和 resume_stage。
- `obsolete` 必须有 obsolete_reason；它表示误建或废弃，不替代 done。
- `done` 前必须有 validation passed、evidence_ref、无未验证项，并且 handoff 不等待、不拒绝。

## evidence / validation / handoff

- evidence 记录已经发生的验证事实。
- validation 是基于 evidence 的判断。
- handoff 是用户验收维度。
- 三者不能互相替代。

不能算 evidence 的例子：

- action note。
- suspicion log。
- doctor clean。
- 测试计划。
- AI 口头判断。
- 用户说“先这样吧”但未确认验收。

## change

以下情况需要 change record 或至少暂停对齐：

- 目标变化。
- 验收口径变化。
- 公开接口或跨服务契约变化。
- 数据结构、权限、环境、部署或真实后果变化。
- 用户临时扩大当前任务范围。

局部实现调整、命名、注释或不改变外部行为的小验证补充，不自动写 change。

## close 与 archive

- `requirement close` 只记录用户确认需求关闭。
- archive authorization 是独立授权。
- archive preflight 必须读取真实 requirement 和 task 状态。
- 只有 done 或 obsolete 的 task 可归档。
- handoff 等待用户验收时不能归档。
