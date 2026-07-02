---
name: workbench-archive
description: Use when Codex 需要在 codex-workbench 中关闭 requirement、做 archive preflight、版本归档或按需读取冷历史。
---

# Workbench Archive

## 核心

Archive 是冷路径。默认恢复现场不展开历史；只有用户要求归档、查历史或发布版本时才触发。

## 步骤

1. 确认 requirement 下任务都已 done 或 obsolete。
2. 确认用户明确关闭需求后，执行 `requirement close --note ...`。
3. 归档前先跑 `archive preflight --authorization-note ...`。
4. 预检通过且用户授权归档后，执行 `archive version --authorization-note ...`。
5. 需要查看历史时用 `archive list`，不要把历史写回 `CURRENT.md`。

## 边界

- requirement closure 不等于 archive authorization。
- archive authorization 不等于用户业务验收。
- 归档不能绕过 validation、handoff 或 evidence。
- 失败时回退本次归档移动和 manifest，不碰外部服务仓库。
