# 核心模型与 schema

本文件记录 v1 的模型边界。机器状态由 YAML 承载，Python 侧用 Pydantic 模型校验；Markdown 只负责解释给人和 Codex 看。

## schema_version

v1 当前只支持：

```yaml
schema_version: "0.1"
```

未知版本必须校验失败。自动迁移不是 v1 默认能力，后续如需要迁移，应由单独任务定义。

状态文件必须显式写出 `schema_version`，工具不应在读取时静默补齐缺失版本。

## 核心对象

- `WorkspaceState`：工作空间入口状态。
- `RequirementState`：需求边界容器，不是执行界面。
- `TaskState`：最小可恢复执行界面。
- `ServiceRegistry`：服务可达性登记；任务可用 `service_refs` 标记相关服务，但它不是修改白名单；写出的 service ref 必须能对应已登记服务。
- `EvidenceState`：验证事实和未验证项。
- `ActionNoteState`：非任务动作记录，`action_type` 只允许 `maintenance_action | ops_action | ephemeral_check`，`status` 只允许 `planned | executed | partial | failed | reverted`，不能替代任务 evidence。
- `ChangeRecordState`：只记录正式 `scope_change`；`implementation_adjustment` 和 `scope_clarification` 只用于轻量分类。
- `DecisionState` / `ArchiveEntryState`：长期决策和版本化冷历史，默认不作为当前记忆。

## Task stage

主阶段保持少量枚举：

```text
draft | ready | in_progress | verification_pending | blocked | done | obsolete
```

review、implementation、validation、handoff、blocked 是维度，不是额外主阶段。

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

- `handoff.status`: `not_required | waiting_user_validation | accepted | rejected`
- `blocked`: reason、blocked_by、resume_condition、resume_stage
- `obsolete_reason`
- `working_scope`
- `likely_touchpoints` / `risk_triggers`

可选字段只有在有真实信息增量时才应写入 YAML 或 Markdown，避免空仪式。review / implementation 的 Markdown 如需生成，使用任务包本地 `review.md` / `implementation.md`，并由 `review.ref` / `implementation.ref` 记录相对引用；它们是解释层，不替代 YAML 中的 review status 或 implementation-ready 结论。

## 知识分层

所有承载事实的对象都可以使用 `Knowledge`：

- `confirmed_facts`
- `system_observations`
- `ai_inferences`
- `assumptions`
- `questions_for_user`

新窗口和生成视图不得把推断升级成确认事实。

## 当前模型边界

本文件只记录 v1 稳定模型和 schema 语义。CLI、doctor、模板、index、service status、hooks 和 skills 可以使用这些模型，但具体行为以对应模块、命令和 policy 为准。
