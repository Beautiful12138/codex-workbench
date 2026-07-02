---
name: workbench-task
description: Use when Codex 需要在 codex-workbench 中处理材料、discovery、intake、requirement、task、阶段推进或任务包边界。
---

# Workbench Task

## 核心

把产品想法先转成可开发需求，再创建任务。不要为普通讨论、头脑风暴或只读探索自动建任务。

## 路由

1. 原始材料只登记脱敏摘要：`material add`。
2. 系统观察、AI 推断、假设和问题进入 `discovery create`。
3. 用户确认后的开发边界进入 `intake create`，再由 `intake confirm` 变成 readable requirement。
4. 正式开发项用 `task create`；`task.yaml.next_step` 记录恢复提示，`task.md` 只生成标题骨架，正文由 AI 按任务填写。
5. 需要显性化 review 或 implementation 时，用 `task review-create` / `task implementation-create` 在任务包本地生成 Markdown；不要预生成空文档。
6. implementation-ready 用 `task prepare` 写入；有暂停条件时加 `--risk-trigger`；阶段推进前可用 `task check --to <stage>` 只读预演，阶段变化用 `task set-stage`。
7. 阻塞任务用 `task block`，必须记录原因、阻塞方、恢复条件和恢复后阶段。
8. 误建或废弃任务用 `task obsolete`，必须保留原因。

## 边界

- Markdown 模板只是起稿骨架，不是固定表单；如果不适合当前任务，标题、章节和表达方式可以自由改。
- `service_refs` 是相关服务标记，不限制后续阅读或必要探索；写出的 service ref 必须能对应已登记服务。
- `risk_triggers` 是暂停确认条件，不是路径白名单。
- 发现新服务、范围变化或验收变化时先暂停对齐。
- 不为“也许以后会用”的内容预生成空 review、implementation、evidence 或 change。
