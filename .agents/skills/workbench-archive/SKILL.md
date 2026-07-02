---
name: workbench-archive
description: Use when Codex 需要在 codex-workbench 中关闭 requirement、做 archive preflight、版本归档或按需读取冷历史。
---

# Workbench Archive

## 适用场景

使用本 skill 处理：

- 用户要求关闭 requirement。
- 用户要求归档一个版本。
- 用户要求查询历史版本。
- 需要判断 task 是否可归档。
- 需要区分用户验收、需求关闭和归档授权。

## 核心原则

Archive 是冷路径。默认恢复现场不展开历史；只有用户要求归档、查历史或恢复旧版本时才读取 archive。

requirement close 不等于 archive authorization。用户业务验收也不等于 archive authorization。

归档不重新判定任务风险。归档前只核对任务是否已经按自身风险和流程门禁闭环：done task 必须有 validation、evidence、handoff；obsolete task 必须有原因。

## 归档前条件

归档 requirement 前必须确认：

- requirement 存在。
- requirement 有用户关闭确认。
- requirement 下所有 task 都是 `done` 或 `obsolete`。
- done task 有通过的 validation、真实 evidence、无未验证项。
- handoff 不等待、不拒绝。
- obsolete task 有原因。
- archive authorization 有明确用户授权说明。

## 标准流程

1. 读取 requirement YAML，确认 task_refs。
2. 读取每个 task YAML。
3. 对 done task 读取 evidence 和 handoff。
4. 若用户只确认任务验收，还不能归档。
5. 用户确认需求关闭后，执行 `requirement close --note ...`。
6. 用户独立授权归档后，执行 `archive preflight --authorization-note ...`。
7. preflight clean 后，执行 `archive version --authorization-note ...`。
8. 归档后按需运行 `index generate` 或 `index check`。

## 冷历史读取

用户问历史版本、已归档需求或旧任务时，用 `archive list` 找版本，再读取对应 archive 包。不要把 archive 历史写回 `CURRENT.md`，也不要让它覆盖当前 active 包事实。

## 失败处理

如果 archive preflight 失败：

- 不要手动移动 active 包。
- 先报告失败原因。
- 按原因回到 requirement、task、evidence、handoff 或 obsolete 状态修复。

如果 archive version 写入失败，工具应回滚本次移动和 manifest；不要碰外部服务仓库。

## 常见反例

- 用户说“这个任务可以了”不等于 requirement close。
- 用户说“验收通过”不等于 archive authorization。
- `doctor clean` 不等于 archive preflight。
- waiting handoff 不能归档。
- failed 或 partial validation 不能当 done 归档。

## 常用命令

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench requirement close REQ-20260702-001 --note "用户确认需求关闭。" --updated-at "2026-07-02"
python -m codex_workbench archive preflight 1.0.0 --requirement-id REQ-20260702-001 --authorization-note "用户确认可以归档版本。" --archived-at "2026-07-02"
python -m codex_workbench archive version 1.0.0 --requirement-id REQ-20260702-001 --authorization-note "用户确认可以归档版本。" --archived-at "2026-07-02"
python -m codex_workbench archive list
```
