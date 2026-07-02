---
name: workbench-resume
description: Use when Codex 需要恢复 codex-workbench 现场、回答当前状态、选择工作对象或决定读取深度。
---

# Workbench Resume

## 适用场景

使用本 skill 处理：

- 新窗口进入 `codex-workbench`。
- 用户问“当前状态”“接下来做什么”“有哪些任务”。
- 用户给出模糊指代，例如“继续那个任务”“看一下当前需求”。
- 需要在多个 requirement、多个 active task、多个 service 中选择工作对象。
- 需要决定是只读探索、写 discovery、推进 task，还是暂停确认。

## 核心原则

`CURRENT.md` 是入口卡，不是完整手册，也不作为单任务锁。工作对象选择必须来自用户请求、显式路径、ID、`docs/generated/recovery.md` 或包 YAML。

generated recovery 是索引，不是真源。判断阶段、范围、验证和交接时，以包 YAML、evidence 和用户确认为准。

## 读取顺序

1. 读 `AGENTS.md`，确认热路径规则。
2. 读 `CURRENT.md`，确认 baseline 或入口提示。
3. 若用户给出显式路径、REQ/TASK ID、服务名，优先读取对应对象。
4. 若没有明确对象，读 `docs/generated/recovery.md`。
5. 若选择到 task，读 `docs/active/<TASK-ID>/task.yaml` 和 `task.md`。
6. 若涉及服务，读 `services/registry.yaml`，必要时运行 `service status`。
7. 若涉及验证、done 或归档，读 evidence、handoff 和对应 policy。

## 工作对象选择

按以下顺序选择：

1. 显式路径优先。
2. 显式 ID 优先于语义推断。
3. 用户语义匹配时，用 recovery 和包 YAML 对齐。
4. 多个 active task 都可能匹配时，优先选择用户最近明确提到的对象。
5. 无法唯一判断且继续会写状态或改文件时，先问用户。

如果只是普通讨论或只读探索，可以继续调查，不必立刻要求用户选择任务。

## 状态回答格式

回答当前状态时，优先说明：

- 当前 workbench 是否 baseline。
- active requirements 数量和重点。
- active tasks 数量、stage、next_step。
- blocked 或 waiting handoff 的任务。
- 已登记服务和缺失服务。
- 当前允许动作。
- 当前禁止动作。
- 建议下一步。

不要把 archive 历史默认展开到当前状态；用户问历史时再查。

## 停止点

遇到以下情况停止推进：

- 工作对象无法唯一判断，但继续会写状态、改文件或推进阶段。
- 目标、范围、验收、服务关系或确认口径不清。
- 触发当前 task 的 `risk_triggers`。
- 要修改外部服务目录、外部环境、真实数据或 Git 状态，但授权不清。
- 用户只是讨论方向，而你必须写状态才能继续。

## 常见反例

- 不要因为 `CURRENT.md` 没有 current_task 就说没有工作可做。
- 不要因为 recovery 里有第一个 active task 就自动选择它。
- 不要用 generated view 覆盖包 YAML。
- 不要把旧聊天摘要当成高层级事实。
- 不要为了恢复现场全量读取 archive。

## 常用命令

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench index check --workspace-root .
python -m codex_workbench doctor check --workspace-root .
python -m codex_workbench service list --workspace-root .
```
