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
- requirement id 使用 `REQ-YYYYMMDD-NNN` 形式，例如 `REQ-20260702-001`。
- task id 使用 `<requirement_id>-TASK-YYYYMMDD-NNN` 形式，例如 `REQ-20260702-001-TASK-20260702-001`。
- `task.yaml:id` 必须以 `task.yaml:requirement_id` 加 `-` 作为前缀。
- requirement 的 `task_refs` 必须引用对应 task id。
- requirement 和 task YAML 都必须写入 `created_at` 与 `updated_at`。`created_at` 是稳定创建时间，`updated_at` 由 CLI 在状态变化时刷新。
- CLI 创建 requirement、intake 草案或 task 时，可以省略 ID 和时间；省略后按当前时间生成日期型 ID，并写入 `created_at` / `updated_at`。

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

`impact_profile` 可用于解释风险和流程档位：

```yaml
impact_profile:
  action: code_change | config_change | data_read | data_write | schema_change | deployment | environment_operation | documentation | analysis
  component_signals:
    - code
    - sql
  environment: local | test | sandbox | personal | shared | production | unknown
  data_effect: none | read_only | test_data_write | real_data_write | schema_or_migration | destructive
  external_effect: none | read_only | write | deploy | notify | cost | security
  blast_radius: self | single_service | multi_service | shared_users | external_users | unknown
  reversibility: git_revert | easy_manual | backup_restore | hard | irreversible | unknown
  contract_change: false | true | unknown
  security_or_permission: false | true | unknown
  verification_confidence: local_testable | integration_required | manual_acceptance_required | unclear
```

`component_signals` 是复杂度线索，不是风险判定白名单或黑名单。`impact_profile` 不替代 `risk_level`、`process_level`、`risk_triggers`、review、implementation、evidence 或用户确认。

`risk_assessment_notes` 只记录风险画像或风险等级调整的原因；它不是 progress，也不替代 change、decision 或 evidence。

完整语义见 `docs/policies/risk-and-process.md`。

## lifecycle 维度

任务可以按需表达：

- `working_scope`
- `likely_touchpoints`
- `risk_triggers`
- `risk_assessment_notes`
- `impact_profile`
- `review.status` / `review.ref` / `review.reviewer` / `review.independent`
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
