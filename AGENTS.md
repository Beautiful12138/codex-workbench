# Codex Workbench 入口地图

本文件是 Codex 进入本工作台后的热路径入口。它的目标不是介绍项目背景，而是让一个新的 Codex 能在**多个需求、多个任务、多个服务**并存时稳定工作：知道读什么、先做什么、何时写状态、何时暂停、何时只讨论。

`codex-workbench` 是个人本地多项目工程协作工作台。它使用文件包承载需求、任务、证据和历史，用 CLI/schema 做可靠写入和门禁，用 generated 视图帮助恢复现场。

## 当前工作区定位

当前仓库同时包含：

- Workbench 运行期 baseline。
- `codex_workbench` Python CLI 与 schema 源码。

`AGENTS.md` 承接稳定入口规则：说明本工作台是什么、如何读取、哪些文件不能手改、什么时候可以写状态。

`CURRENT.md` 是 CLI 生成的动态当前工作面板，展示最近活跃任务；它不作为单任务锁。真实工作对象必须从用户请求、显式包路径、`docs/generated/recovery.md`、CLI 参数或包 YAML 中选择。

## 启动读取顺序

恢复现场、回答状态问题或准备行动时，按以下顺序读取：

1. `AGENTS.md`
2. `CURRENT.md`
3. 用户明确给出的路径、任务 ID、需求 ID 或服务名
4. `docs/generated/recovery.md`
5. 被选中的 requirement / task 包 YAML 与 Markdown
6. 仅在动作需要时读取对应 policy、`services/registry.yaml` 或 `docs/archive/`*

普通讨论不需要展开全部状态。只读探索不等于修改授权。生成视图只用于定位和恢复，不能覆盖包 YAML 真源。

创建 requirement、intake 草案或 task 时，CLI 可自动生成日期型 ID 和当前时间；显式 ID 主要用于复现、导入或用户已经指定对象的场景。

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

## 风险入口

风险按真实后果判断，不按组件名判断。DB、SQL、Redis、MQ、Docker、配置、脚本和依赖升级只是风险线索，不能单独决定流程等级。

判断风险时先问五件事：

1. 这次是否会写真实项目资产、数据、环境或外部系统？
2. 环境是 local、sandbox、personal、shared、production 还是 unknown？
3. 是否影响真实数据、权限、安全、部署、费用、外部通知或他人？
4. 是否改变接口、schema、跨服务契约、索引、消息格式或验收口径？
5. 是否可验证、可回滚，授权是否清楚？

出现真实数据、生产/共享环境、权限安全、部署发布、不可逆、费用、外部通知、影响他人、环境不清、授权不清或回滚不清时，暂停确认或加严流程。完整规则见 `docs/policies/risk-and-process.md`。

## 工作对象选择

多需求、多任务并存时，按以下优先级选择工作对象：

1. 显式路径优先：用户给出 `docs/active/...`、文件路径、任务包路径或服务路径时，以它为候选对象。
2. 显式 ID 其次：用户点名 `REQ-YYYYMMDD-NNN`、`REQ-YYYYMMDD-NNN-TASK-YYYYMMDD-NNN`、`EV-*`、action/change/decision/suspicion ID 时，读取对应包。
3. 用户语义匹配：用户说“刚才那个任务”“这个需求”“某服务的问题”时，用 `docs/generated/recovery.md` 和包 YAML 对齐。
4. recovery 辅助：没有明确对象时，先读 `docs/generated/recovery.md`，从 active task、blocked、next_step、service_refs 和 conflicts 中选择。
5. 无法唯一判断时，保持只读，不写状态，向用户问一个聚焦问题。

不要因为 `CURRENT.md` 没有某个任务就认为没有可推进任务；也不要因为 `CURRENT.md` 提到某个对象就忽略用户当前明确指定的对象。

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
- `CURRENT.md` / `docs/generated/index.md` / `docs/generated/recovery.md`：可重建视图，不覆盖真源。
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

## 生命周期入口

产品工作从 material / discovery / intake 进入 readable requirement，再创建 task、准备 implementation-ready、实现、验证、handoff、done、requirement close 和 archive。具体命令和门禁不要在本入口卡展开；执行时使用 `workbench-task`、`workbench-evidence`、`workbench-archive` 和对应 policy。

轻量路径只减少空仪式，不跳过事实、范围、风险、验证和完成门禁。

## Policy 地图

- `docs/policies/action-routing.md`：请求分流、状态写入边界和反例。
- `docs/policies/risk-and-process.md`：风险判断、影响面画像和流程档位。
- `docs/policies/recovery-and-concurrency.md`：工作对象选择、多包并发和恢复规则。
- `docs/policies/state-and-gates.md`：阶段、门禁、验证、交接、完成和归档。
- `docs/policies/materials.md`：材料、discovery、intake 和事实边界。
- `docs/policies/services-and-environment.md`：服务登记、多服务协作、环境和 Git 边界。
- `docs/policies/agent-coordination.md`：skills、子代理、复核和接续方式。
- `docs/policies/lifecycle-semantics.md`：生命周期语义。
- `docs/policies/model-schema.md`：核心模型和 schema 语义。

## 本地 Skills

本仓库的 Workbench skills 位于 `.agents/skills/`，以本仓库版本为准。

- `workbench-resume`：恢复现场和选择工作对象。
- `workbench-task`：材料、需求、任务、风险画像、准备和阶段推进。
- `workbench-evidence`：证据、validation、handoff 和 done。
- `workbench-archive`：requirement close、archive 授权和冷历史。

skills 是操作规程；状态修改仍通过 CLI 和包 YAML 完成。

## 自动提醒与健康检查

`.codex/hooks.json` 只提供轻量提醒，不写状态、不运行 doctor、不推进阶段、不归档。`doctor check` 是只读健康检查，只报告机器真源和 lifecycle 的硬问题；它不是流程教练，不能替代人工判断、evidence、用户验收或风险接受。
