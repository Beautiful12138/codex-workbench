# 核心模型与 schema

本文件记录运行期状态模型边界。机器状态由 YAML 承载，Python 侧用 Pydantic 模型校验；Markdown 只负责解释给人和 Codex 看。

## schema_version

当前支持：

```yaml
schema_version: "0.1"
```

状态文件必须显式写出 `schema_version`。读取时不静默补齐缺失版本；未知版本校验失败。

## 核心对象

- `WorkspaceState`：工作空间入口状态。
- `RequirementState`：需求边界容器，不是执行界面。
- `TaskState`：最小可恢复执行界面。
- `ServiceRegistry`：服务登记和可达性输入；`service_refs` 不是修改白名单。
- `EvidenceState`：验证事实、结论和未验证项。
- `ActionNoteState`：非任务动作记录，不能替代任务 evidence。
- `ChangeRecordState`：正式范围、验收、契约或真实后果变化记录。
- `DecisionState`：长期决策，默认冷路径。
- `SuspicionState`：疑点线索，防止证据不足时静默优化。
- `ArchiveManifestState`：版本归档清单。

## Task stage

主阶段保持少量枚举：

```text
draft | ready | in_progress | verification_pending | blocked | done | obsolete
```

`review`、`implementation`、`validation`、`handoff`、`blocked` 是维度，不是额外主阶段。

## task 归属

任务包的机器真源是 `task.yaml`：

- `id` 是全局唯一 task id。
- `requirement_id` 是所属 requirement id。
- 新 task id 使用 `<requirement_id>-TASK-...` 形式，例如 `REQ-001-TASK-001`。
- `task.yaml:id` 必须以 `task.yaml:requirement_id` 加 `-` 作为前缀。
- requirement 的 `task_refs` 必须引用对应 task id。

任务包内 Markdown 标题应带完整 task id，帮助人和 Codex 阅读；机器校验不从 Markdown 反推归属。

## process 与 risk

`process_level` 表达显性化强度：

```text
micro | lightweight | standard | high | critical
```

`risk_level` 表达风险等级：

```text
low | standard | high | critical
```

轻量路径只减少仪式和文件数量，不跳过状态 guard。

## lifecycle 维度

任务可以按需表达：

- `working_scope`
- `likely_touchpoints`
- `risk_triggers`
- `review.status` / `review.ref`
- `implementation.ready` / `implementation.conclusion` / `implementation.ref`
- `validation.status` / `validation.evidence_ref` / `validation.unverified_items`
- `handoff.status` / `handoff.note`
- `blocked.reason` / `blocked.blocked_by` / `blocked.resume_condition` / `blocked.resume_stage`
- `obsolete_reason`

可选字段只有在有真实信息增量时才写入，避免空仪式。

## 知识分层

承载事实的对象可以使用 `Knowledge`：

- `confirmed_facts`
- `system_observations`
- `ai_inferences`
- `assumptions`
- `questions_for_user`

新窗口和 generated view 不能把推断升级成确认事实。

## Markdown 边界

Markdown 是解释层，不是机器状态真源。CLI 可以生成标题骨架，但不应把 YAML 大段复读进 Markdown。任务正文由 Codex 根据真实场景填写。
