---
name: workbench-resume
description: Use when Codex 需要恢复 codex-workbench 现场、回答当前状态、选择工作对象或决定读取深度。
---

# Workbench Resume

## 核心

先把 `CURRENT.md` 当入口卡，不把它当完整手册。它只回答当前工作区状态、入口提示，以及如何从用户请求、生成视图、CLI 参数或明确包路径选择工作对象。

## 步骤

1. 读 `CURRENT.md`。
2. 按用户请求选择工作对象：明确路径优先，其次 generated recovery、CLI 参数或用户指定任务。
3. 若要改文件，先读被选中的任务包；只讨论或只读探索时不写状态。
4. 需要查看服务时读 `services/registry.yaml`；`service_refs` 只是相关服务标记，不是修改白名单。
5. generated 视图只做索引；判断状态以包 YAML 为准。

## 停止点

- 目标、范围、验收或确认口径不清。
- 触发当前任务写明的 `risk_triggers`。
- 用户只是讨论方向，却需要写状态才能继续。
- 要修改外部服务目录、外部环境或真实 Git 状态。
