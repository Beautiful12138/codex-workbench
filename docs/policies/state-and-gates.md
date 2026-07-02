# 状态与门禁

本文件说明 Workbench 的最小阶段语义。机器状态以包 YAML 为准，Markdown 用于解释。

## 需求入口

- 原始聊天、截图、材料和 AI 推断不是可开发事实。
- material 只登记来源和脱敏摘要；discovery 记录观察、推断、假设和问题。
- intake 经用户确认后，`readiness.status=readable` 且 `confirmed_by_user=true`，才允许创建正式 task。

## 任务推进

- task 是执行界面，优先读 YAML 中的目标、完成口径、范围、服务引用、事实、验证要求和 `next_step` 恢复提示；Markdown 是 AI 可自由整理的人读说明。
- 工作产物 Markdown 骨架来自 `templates/work-products/`，只用于稍微统一格式；标题、章节和表达方式可按当前任务自由删改。review 和 implementation 需要显性化时放在任务包本地 `review.md` / `implementation.md`。
- 阶段推进前可用 `task check --to <stage>` 只读预演门禁；它不写状态，也不替代 AI 判断。
- 修改任务目标内文件前，task 必须处于 `in_progress`，并且 implementation-ready 已说明范围、风险触发器、验证和回滚；最小状态用 `task prepare` 写入。
- `service_refs` 只是相关服务标记；修改授权来自用户请求、任务阶段、working_scope 和风险边界。写出的 service ref 必须对应已登记服务。
- `risk_triggers` 是暂停确认条件，不是路径白名单；触发后先对齐再继续。
- `high` / `critical` 的 `risk_level` 或 `process_level` 进入 `in_progress` 前，还需要 review done、implementation ref、working_scope、risk_triggers 和风险接受说明。

## 阻塞和废弃

- `task block` 必须记录 reason、blocked_by、resume_condition 和 resume_stage。
- `task obsolete` 用于误建或废弃任务，必须保留原因；obsolete 不等于 done，也不替代 validation。

## 验证和完成

- evidence 记录已经发生的验证事实，不能由计划或口头判断替代。
- validation apply 只把 evidence 的判断写回 task；`passed` 必须显式确认。
- handoff 记录用户验收维度；等待或拒绝验收时不能 done。
- done 前必须有通过的 validation、evidence 引用、无未验证项，并且 handoff 不阻塞。

## 归档

- requirement close 只是需求关闭确认，不等于归档授权。
- archive preflight / version 必须读取真实 requirement 和 task 状态。
- 归档后的历史是冷路径，只在查询、生成 index 或恢复旧版本时读取。
