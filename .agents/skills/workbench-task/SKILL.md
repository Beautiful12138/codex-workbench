---
name: workbench-task
description: Use when Codex 需要在 codex-workbench 中处理材料、discovery、intake、requirement、task、阶段推进或任务包边界。
---

# Workbench Task

## 适用场景

使用本 skill 处理：

- 用户希望把想法、问题或材料纳入 Workbench。
- 创建或确认 requirement。
- 创建 task。
- 处理 task prepare、阶段推进、blocked 或 obsolete。
- 处理涉及测试环境、服务器、数据库、GitLab、网站、联调、账号密码或操作方式的任务。
- 判断当前请求是普通讨论、只读探索、小修、正式任务、维护动作还是外部环境动作。

## 核心原则

Workbench 的任务包是为了让 Codex 更好地服务需求，不是为了制造流程。先接住用户要做什么；只有事情需要可恢复、可验证、可交接或长期跟踪时，才进入正式任务包。

产品任务必须从可读需求出发。原始材料、截图、聊天摘要、AI 推断和只读探索结果都不能直接当成可开发事实。

默认入口先看 `workspace context`；选中 task 后再进入 `task context`。不要为了普通讨论提前读取完整包。

`CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md` 只辅助定位；创建、阶段、风险、验证和交接以包 YAML、evidence、用户确认和命令输出为准。

轻量路径只减少空仪式，不跳过目标、范围、验证、交接和完成门禁。

风险按真实后果判断，不按组件名判断。DB、SQL、Redis、MQ、配置、部署、脚本、依赖升级只是线索；真实数据、生产/共享环境、权限安全、部署、不可逆、影响他人、契约变化、验证或回滚不清时，暂停或加严。

## 路由流程

先判断用户请求落在哪一类：

| 请求类型 | 怎么做 |
| --- | --- |
| 普通讨论 | 只回答或一起思考，不写状态。 |
| 只读探索 | 读文件、日志、`service context` 或 `environments/`；用户要求纳入 Workbench，或会影响后续恢复时再写 discovery。 |
| small-fix | 用户明确授权、影响清楚、低风险、可验证、可回滚时，最小修改和验证；不自动创建正式 task。 |
| codex-workbench 自身维护 | 默认走 `maintenance_action / repo maintenance`，不强制创建 requirement/task。 |
| 新需求 | 先 material / discovery / intake，用户确认边界后再 requirement/task。 |
| 正式执行项 | 创建 task，准备 working_scope、风险画像、验证和交接。 |
| 外部环境动作 | 先读 `workbench-environment` 和 `environments/`，确认授权和风险。 |

工作面板：选择到 task 或创建 task 后，用 `task context <任务名或ID>` 看当前能做什么、缺什么、服务是否可接。对用户回复优先任务名称，ID 主要用于命令和消歧。

## 正式任务进入

正式任务通常按这个顺序进入：

1. `material add` 只记录来源和脱敏摘要。
2. `discovery create` 记录观察、推断、假设和待确认问题。
3. `intake create` 形成 AI-readable 需求草案。
4. `intake confirm` 固定用户确认的需求边界。
5. `task create` 创建可执行任务。
6. `task context` 看工作面板。
7. `task prepare` 固定本次工作范围、风险触发器、验证和回滚思路。
8. `task check --to <stage>` 做阶段预演，通过后再 `task set-stage`。

创建 requirement、intake 草案或 task 时，优先让 CLI 自动生成 ID 和当前时间；只有用户指定、导入历史或复现测试时才手写 ID。创建后读取 CLI 回显，内部命令可用 ID；回复用户默认说任务名称。

## 风险画像

创建或准备 task 时，先用以下问题形成影响面画像：

- `action`：这次主要是代码、配置、数据、schema、部署、环境操作、文档还是分析？
- `component_signals`：出现了哪些组件线索，例如 SQL、DB、Redis、配置、脚本或外部服务？
- `environment`：目标环境是 local / test / sandbox / personal / shared / production / unknown，也就是 local、test、sandbox、personal、shared、production、unknown；不清楚就按 unknown，并在写状态、改文件或改环境前确认。
- `data_effect`：是否只读、写测试数据、写真实数据、改 schema/migration 或破坏数据？
- `external_effect`：是否会部署、通知、产生费用、影响安全或写外部系统？
- `blast_radius`：只影响自己、单服务、多服务、共享用户、外部用户还是未知？
- `reversibility`：可 git revert、易手工恢复、需备份恢复、困难、不可逆还是未知？
- `contract_change`：是否改变接口、schema、索引、消息格式、跨服务契约或验收口径？
- `security_or_permission`：是否涉及权限、认证、安全、密钥、token、账号或隐私？
- `verification_confidence`：是否能本地验证、需要联调、需要人工验收或路径不清？

涉及测试环境、服务器、数据库、GitLab、网站、联调、账号密码或操作方式时，先查 `environments/`。该目录是自由 Markdown，不要求固定字段；信息缺失时不要猜。

`component_signals` 不能单独决定高风险。一个本地测试 SQL 可以是 low/micro；生产库 DDL、真实数据批量 update/delete 必须 high/critical。

## risk/process 选择

- `micro`：只用于 low 风险、范围很小、本地可验证、可 git 回滚的任务。
- `lightweight`：用于小范围真实任务；需要 task、prepare、evidence，review 和 implementation 可内联。
- `standard`：用于正常工程任务；需要清楚 scope、implementation-ready、验证和回滚。
- `high` / `critical`：用于真实后果、高不确定性或较大影响面；必须有 independent review、implementation ref、risk_triggers、风险接受和验证计划。独立复核优先用子代理。

遇到 environment、data_effect、external_effect、blast_radius、reversibility、contract_change、security_or_permission 或 verification_confidence 为 unknown/unclear，且继续会写状态或改文件时，先暂停确认。

高风险或 critical task 进入 `in_progress` 前必须有 `impact_profile`。如果当前 task 已创建但缺风险画像，先用 `task impact-set` 或在 `task prepare` 中补齐。

已有 `impact_profile` 时，`task prepare` / `task impact-set` 可以局部覆盖：只传变化字段并合并旧值；新建画像仍必须有 `action`。

## task prepare

进入实现前，`task prepare` 至少固定这些东西：

- working_scope：本次允许工作的范围。
- risk_triggers：触发暂停确认的条件。
- likely_touchpoints：预计触点，用于恢复，不是路径白名单。
- implementation ref：需要显性化时指向 `implementation.md`。
- review ref：高风险任务需要 independent review done；个人本地工作台优先让子代理复核。
- risk acceptance：高风险或真实后果任务需要用户确认。

不要把 `service_refs` 当成修改白名单。它只是相关服务标记。

## 阶段推进

- `draft`：草案任务。
- `ready`：已准备但未开工。
- `in_progress`：可修改任务范围内文件。
- `verification_pending`：实现后等待验证。
- `blocked`：外部条件阻塞，必须有恢复条件。
- `done`：验证和交接闭环。
- `obsolete`：误建或废弃，不等于完成。

`verification_pending` / `handoff.status=waiting_user_validation` 是等待反馈，不是 blocked。收到用户反馈“测过了/可以关掉”后，先补 evidence / validation / handoff，再判断能否 done。

阶段推进前先用 `task check`。失败时不要绕过 lifecycle guard。

## 变更判断

以下情况先暂停并考虑 change record：

- 用户目标变化。
- 完成口径变化。
- 公开契约或跨服务接口变化。
- 数据结构、权限、部署、环境或真实后果变化。
- 临时扩大正式范围。

局部命名、注释、文案、小范围验证补充，且不改变目标和风险时，不自动升级为 change。

## small-fix 边界

`small-fix` 只适用于用户已明确授权、影响面清楚、低风险、可本地验证、可回滚的小型修改。它不能用来绕过风险公式，也不能用来替代产品任务流程。

如果修改影响范围、验收、服务契约、数据、权限、部署、外部系统、共享环境、真实后果，或验证/回滚不清，先按 `risk-and-process.md` 升级为正式 task 或 ops_action。不能用 small-fix 绕过风险公式、用户授权或必要验证。

## 不能做的事

- 不为普通讨论创建 task。
- 不为只读探索默认写状态。
- 不创建没有用户确认的 readable requirement 的正式 task。
- 不预生成空 review、implementation、evidence 或 change。
- 不用 action note 替代产品任务。
- 不能用 small-fix 绕过风险公式、用户授权或必要验证。

## 常用命令

本 skill 只给出入口，参数用 `workbench-cli` 和 `--help` 核对。

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench workspace context --workspace-root .
python -m codex_workbench task context "任务名称"
python -m codex_workbench task create --help
python -m codex_workbench task prepare --help
python -m codex_workbench task impact-set --help
python -m codex_workbench task check --help
python -m codex_workbench task set-stage --help
```
