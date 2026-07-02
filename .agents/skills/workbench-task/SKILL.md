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
- 判断当前请求是产品任务、维护动作还是只读探索。

## 核心原则

产品任务必须从可读需求出发。原始材料、截图、聊天摘要、AI 推断和只读探索结果都不能直接当成可开发事实。

轻量路径只减少空仪式，不跳过目标、范围、验证、交接和完成门禁。

## 路由流程

1. 普通讨论：不写状态。
2. 只读探索：先读文件、日志或服务状态；需要沉淀时写 discovery。
3. 原始材料：用 `material add` 记录来源和脱敏摘要。
4. 系统观察、AI 推断、假设和问题：用 `discovery create`。
5. AI-readable 需求草案：用 `intake create`。
6. 用户确认需求边界：用 `intake confirm`。
7. 正式执行项：用 `task create`。
8. 开工准入：用 `task prepare` 写入 working_scope、risk_triggers、implementation-ready。
9. 阶段预演：用 `task check --to <stage>`。
10. 阶段写入：用 `task set-stage --stage <stage>`。

## task prepare

进入实现前，`task prepare` 至少应固定：

- working_scope：本次允许工作的范围。
- risk_triggers：触发暂停确认的条件。
- likely_touchpoints：预计触点，用于恢复，不是路径白名单。
- implementation ref：需要显性化时指向 `implementation.md`。
- review ref：高风险任务需要 review done。
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

阶段推进前先用 `task check`。失败时不要绕过 lifecycle guard。

## 变更判断

以下情况先暂停并考虑 change record：

- 用户目标变化。
- 完成口径变化。
- 公开契约或跨服务接口变化。
- 数据结构、权限、部署、环境或真实后果变化。
- 临时扩大正式范围。

局部命名、注释、文案、小范围验证补充，且不改变目标和风险时，不自动升级为 change。

## 不能做的事

- 不为普通讨论创建 task。
- 不为只读探索默认写状态。
- 不创建没有用户确认的 readable requirement 的正式 task。
- 不预生成空 review、implementation、evidence 或 change。
- 不用 action note 替代产品任务。

## 常用命令

创建 requirement、intake 草案或 task 时，优先让 CLI 自动生成 ID 和当前时间；只有用户指定、导入历史或复现测试时才手写 ID。

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench material add MAT-001 --title "..." --source "..." --summary "..." --received-at "..."
python -m codex_workbench discovery create DISC-001 --title "..." --material-ref MAT-001 --updated-at "..."
python -m codex_workbench intake create --title "..." --goal "..." --acceptance "..." --material-ref MAT-001
python -m codex_workbench intake confirm REQ-20260702-001 --updated-at "..."
python -m codex_workbench task create --requirement-id REQ-20260702-001 --title "..." --user-goal "..." --done "..." --next "..."
python -m codex_workbench task prepare REQ-20260702-001-TASK-20260702-001 --working-scope "..." --risk-trigger "..."
python -m codex_workbench task check REQ-20260702-001-TASK-20260702-001 --to in_progress
python -m codex_workbench task set-stage REQ-20260702-001-TASK-20260702-001 --stage in_progress
```
