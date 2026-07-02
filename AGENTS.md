# Codex Workbench 入口地图

本文件是 Codex 进入本工作台后的热路径入口。它的目标不是介绍项目背景，而是让一个新的 Codex 能在**多个需求、多个任务、多个服务**并存时稳定工作：知道读什么、先做什么、何时写状态、何时暂停、何时只讨论。

`codex-workbench` 是个人本地多项目工程协作工作台。它使用文件包承载需求、任务、证据和历史，用 CLI/schema 做可靠写入和门禁，用 generated 视图帮助恢复现场。

## 当前工作区定位

当前仓库同时包含：

- Workbench 运行期 baseline。
- `codex_workbench` Python CLI 与 schema 源码。

`CURRENT.md` 是入口卡，只提供第一眼恢复提示；它不作为单任务锁。真实工作对象必须从用户请求、显式包路径、`docs/generated/recovery.md`、CLI 参数或包 YAML 中选择。

## 启动读取顺序

恢复现场、回答状态问题或准备行动时，按以下顺序读取：

1. `AGENTS.md`
2. `CURRENT.md`
3. 用户明确给出的路径、任务 ID、需求 ID 或服务名
4. `docs/generated/recovery.md`
5. 被选中的 requirement / task 包 YAML 与 Markdown
6. 仅在动作需要时读取对应 policy、`services/registry.yaml` 或 `docs/archive/`*

普通讨论不需要展开全部状态。只读探索不等于修改授权。生成视图只用于定位和恢复，不能覆盖包 YAML 真源。

## 请求分流

先判断用户请求属于哪类，再决定读写深度：


| 类型   | 典型请求                      | 默认动作                                               |
| ---- | ------------------------- | -------------------------------------------------- |
| 普通讨论 | 解释、比较、判断方向、问是否合理          | 只读最少上下文，不写状态                                       |
| 只读探索 | 看文件、看服务状态、看日志、定位问题        | 可搜索和读取，不写状态；若后续要沉淀需求再写 discovery                   |
| 产品任务 | 用户要实现、修复、调整可交付功能          | material / discovery / intake / task / evidence 流程 |
| 维护动作 | 整理 Workbench 自身、局部文档或工具维护 | 必要时写 action note；不伪装成产品任务                          |
| 运维动作 | 环境、权限、配置、部署、运行状态、外部服务写入   | 先确认授权；需要留痕时写 action note                           |
| 临时检查 | 一次性状态确认、临时诊断              | 通常不落档；若支撑后续决策再写 discovery 或 action                 |
| 归档动作 | 需求关闭、版本归档、查询历史            | 需要需求关闭确认和独立归档授权                                    |


如果不确定性不影响只读调查，先调查并说明假设。若不确定性会影响代码、配置、数据、权限、安全、部署、外部环境或完成结论，先暂停确认。

## 工作对象选择

多需求、多任务并存时，按以下优先级选择工作对象：

1. 显式路径优先：用户给出 `docs/active/...`、文件路径、任务包路径或服务路径时，以它为候选对象。
2. 显式 ID 其次：用户点名 `REQ-*`、`REQ-*-TASK-*`、`EV-*`、action/change/decision/suspicion ID 时，读取对应包。
3. 用户语义匹配：用户说“刚才那个任务”“这个需求”“某服务的问题”时，用 `docs/generated/recovery.md` 和包 YAML 对齐。
4. recovery 辅助：没有明确对象时，先读 `docs/generated/recovery.md`，从 active task、blocked、next_step、service_refs 和 conflicts 中选择。
5. 无法唯一判断时，保持只读，不写状态，向用户问一个聚焦问题。

不要因为 `CURRENT.md` 没有 current_task 就认为没有可推进任务；也不要因为 `CURRENT.md` 提到某个对象就忽略用户当前明确指定的对象。

## 读取深度


| 当前动作 | 默认读取                                                    | 展开条件                         |
| ---- | ------------------------------------------------------- | ---------------------------- |
| 普通讨论 | `AGENTS.md`、`CURRENT.md`、用户指定材料                         | 需要固化结论时再读 policy 或包          |
| 只读探索 | 用户指定文件、recovery、相关服务状态                                  | 需要形成 discovery / intake 时再落档 |
| 需求梳理 | material、discovery、intake 草案                            | 用户确认后才 readable              |
| 任务创建 | readable requirement、服务登记、相关 discovery                  | 范围或验收不清时暂停                   |
| 任务推进 | task YAML、task.md、service registry、implementation-ready | 改文件前确认 task 已 `in_progress`  |
| 验证收口 | task、evidence、validation、handoff                        | 标 done 前必须读取真实 evidence      |
| 归档   | requirement、done/obsolete task、archive policy           | 需要 close 确认和 archive 授权      |


## 状态真源

- `docs/active/*/*.yaml`：requirement、task、evidence 的机器状态真源。
- `docs/active/*/*.md`：给人和 Codex 的解释层，不覆盖 YAML。
- `services/registry.yaml`：服务登记和只读状态输入。
- `docs/generated/index.md` / `docs/generated/recovery.md`：可重建视图，不覆盖真源。
- `docs/archive/`：版本化冷历史，默认不作为当前上下文。
- `docs/actions/`、`docs/changes/`、`docs/decisions/`、`docs/suspicions/`：非任务动作、范围变化、长期决策和疑点线索。

事实层级从高到低：

```text
人工明确确认 / 命令输出 / 真实文件状态
> evidence
> action note
> requirement / task YAML
> discovery
> generated view
> task next_step
> AI 推断
> 未确认假设
```

低层级不能覆盖高层级。冲突无法裁决时，保守处理并报告。

## 修改边界

- 没有用户确认的 readable requirement，不创建正式产品 task。
- 没有 `in_progress` task 和清楚 implementation-ready，不修改任务目标内文件。
- `service_refs` 是相关服务标记，不是修改白名单；修改授权来自用户请求、任务阶段、working_scope、风险边界和必要确认。
- 发现新服务、范围变化、验收变化、外部契约变化或真实后果变化时，暂停对齐。
- 真实数据、部署、安全、权限、费用、不可逆操作、影响他人或共享环境时，必须先确认。
- 没有 evidence，不声称已验证或已完成。
- action note、doctor clean、测试计划、口头判断都不能替代 task evidence。

## 任务生命周期

产品工作通常按以下闭环推进：

1. `material add`：登记来源和脱敏摘要。
2. `discovery create`：记录只读探索得到的观察、推断、假设和问题。
3. `intake create`：形成 AI-readable 需求草案。
4. `intake confirm`：用户确认后 requirement 才 readable。
5. `task create`：创建任务包。
6. `task review-create` / `task implementation-create`：需要显性化时在任务包本地创建说明。
7. `task prepare`：写入 working_scope、risk_triggers、implementation-ready 等开工准入。
8. `task set-stage --stage in_progress`：通过门禁后进入实现。
9. `evidence create`：记录真实验证事实。
10. `validation apply`：基于 evidence 写回验证结论。
11. `handoff set`：记录用户验收维度。
12. `task set-stage --stage done`：validation、evidence、handoff 均满足时完成。
13. `requirement close`：用户确认需求关闭。
14. `archive preflight` / `archive version`：独立授权后版本归档。

轻量路径只减少空仪式，不跳过事实、范围、验证和完成门禁。

## Policy 地图

- `docs/policies/action-routing.md`：请求分流、状态写入边界和反例。
- `docs/policies/recovery-and-concurrency.md`：工作对象选择、多包并发和恢复规则。
- `docs/policies/state-and-gates.md`：阶段、门禁、验证、交接、完成和归档。
- `docs/policies/materials.md`：材料、discovery、intake 和事实边界。
- `docs/policies/services-and-environment.md`：服务登记、多服务协作、环境和 Git 边界。
- `docs/policies/agent-coordination.md`：skills、子代理、复核和接续方式。
- `docs/policies/lifecycle-semantics.md`：生命周期语义。
- `docs/policies/model-schema.md`：核心模型和 schema 语义。

## 本地 Skills

本仓库的 Workbench skills 位于 `.agents/skills/`，以本仓库版本为准。

- `workbench-resume`：恢复现场、选择工作对象、决定读取深度。
- `workbench-task`：材料、需求、任务、准备和阶段推进。
- `workbench-evidence`：证据、验证、交接和 done 判断。
- `workbench-archive`：需求关闭、归档授权、预检和冷历史读取。

skills 是操作规程；状态修改仍通过 CLI 和包 YAML 完成。

## 自动提醒与健康检查

`.codex/hooks.json` 只提供轻量提醒，不写状态、不运行 doctor、不推进阶段、不归档。`doctor check` 是只读健康检查，只能报告状态问题，不能替代人工判断、evidence、用户验收或风险接受。