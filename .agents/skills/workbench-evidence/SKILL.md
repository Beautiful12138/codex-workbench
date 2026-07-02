---
name: workbench-evidence
description: Use when Codex 需要在 codex-workbench 中记录 evidence、应用 validation、处理 handoff 或判断任务能否 done。
---

# Workbench Evidence

## 核心

Evidence 记录已经发生的验证事实；Validation 是基于 evidence 的判断；Handoff 是用户验收维度。三者不能互相替代。

## 步骤

1. 跑过测试、命令、检查或人工验收后，才用 `evidence create`。
2. 用 `validation apply` 把 evidence 结论写回 `task.yaml`。
3. 需要用户验收时用 `handoff set --status waiting_user_validation`。
4. 用户明确接受或拒绝后，用 `handoff set --status accepted|rejected --note ...`。
5. 只有 validation passed、无未验证项、handoff 已解决时，才尝试 `task set-stage --stage done`。

## 反例

- Action note 不是 evidence。
- Action note 只记录非任务动作类型，不支撑任务验证。
- Suspicion log 不是 evidence。
- `doctor clean` 不能替代当前任务验证。
- 没有 evidence 时，不说“已验证”或“已完成”。
