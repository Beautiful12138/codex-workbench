---
name: workbench-evidence
description: Use when Codex 需要在 codex-workbench 中记录 evidence、应用 validation、处理 handoff 或判断任务能否 done。
---

# Workbench Evidence

## 适用场景

使用本 skill 处理：

- 创建 evidence。
- 把 evidence 结论应用到 task validation。
- 记录 handoff。
- 判断 task 是否能 done。
- 区分验证事实、用户验收、doctor、action note 和 AI 判断。

## 核心原则

Evidence 记录已经发生的验证事实；Validation 是基于 evidence 的判断；Handoff 是用户验收维度。三者不能互相替代。

没有 evidence 时，不说“已验证”或“已完成”。`doctor clean` 也不能替代当前任务验证。

gate-check 结果不能作为交付 evidence；它只能说明门禁预演或阻塞诊断发现了什么，不能替代任务本身的交付验证事实。

风险越高，evidence 越要能证明真实后果已被验证或明确例外处理。high/critical、真实数据、生产/共享环境、权限安全、部署、不可逆、影响他人或契约变化任务，不能只用本地静态检查支撑 `passed`，除非 task 明确说明这些风险未实际触发或已有用户确认的验收边界。

## 记录 evidence 前

确认已经发生了真实验证，例如：

- 测试命令已经运行。
- 构建命令已经运行。
- 只读检查有明确输出。
- 用户明确完成验收。
- 外部环境验证有命令、日志或用户确认支撑。

Evidence 的 key_outputs 应摘要关键输出，不复制长日志，不写敏感数据。

如果验证路径、环境、授权或回滚不清，先让 task 保持 `verification_pending` 或 `blocked`，不要用 partial 输出伪装成 passed。

## 标准流程

1. 运行验证命令或取得人工验收事实。
2. 用 `evidence create` 写 evidence。
3. 用 `validation apply` 把 evidence 结论写回 task。
4. 如需用户验收，用 `handoff set --status waiting_user_validation`。
5. 用户明确接受或拒绝后，用 `handoff set --status accepted|rejected --note ...`。
6. 用 `task check --to done` 预演。
7. 门禁通过后，用 `task set-stage --stage done`。

## 不能算 evidence

以下内容不能算 evidence：

- Action note。
- Suspicion log。
- Discovery。
- Generated view。
- `doctor clean`。
- gate-check 输出或 `task check` 预演结果。
- 测试计划。
- AI 自己说“应该可以”。
- 用户只说“继续吧”，但没有验收含义。

## validation 规则

- `validation apply` 的 status 必须与 evidence conclusion 一致。
- `passed` 不能有 unverified_items。
- evidence 必须属于当前 task。
- evidence ref 不能指向其他 task 或 archive 路径。

## handoff 规则

- `waiting_user_validation` 表示等待用户验收，不能 done。
- `accepted` 必须有 note。
- `rejected` 必须有 note，且不能 done。
- `not_required` 可用于无需用户验收的任务，但仍不能跳过 evidence。

## done 判断

task 能 done 必须同时满足：

- validation status 是 `passed`。
- validation 有 evidence_ref。
- validation 无未验证项。
- evidence 真实存在且属于该 task。
- handoff 不等待、不拒绝；若 accepted 必须有 note。

## 常用命令

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench evidence create EV-REQ-20260702-001-TASK-20260702-001 --task-id REQ-20260702-001-TASK-20260702-001 --conclusion passed --key-output "python -m pytest passed" --updated-at "2026-07-02"
python -m codex_workbench validation apply REQ-20260702-001-TASK-20260702-001 --evidence-id EV-REQ-20260702-001-TASK-20260702-001 --status passed
python -m codex_workbench handoff set REQ-20260702-001-TASK-20260702-001 --status waiting_user_validation
python -m codex_workbench handoff set REQ-20260702-001-TASK-20260702-001 --status accepted --note "用户确认验收通过。"
python -m codex_workbench task check REQ-20260702-001-TASK-20260702-001 --to done
python -m codex_workbench task set-stage REQ-20260702-001-TASK-20260702-001 --stage done
```
