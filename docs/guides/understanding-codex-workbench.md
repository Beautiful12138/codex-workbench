# 理解 codex-workbench

`codex-workbench` 是给 Codex 使用的本地工程协作工作台。它不是业务项目，也不是 issue 系统，而是一套帮助 Codex 在长对话、多任务、多服务和跨天继续时保住现场、事实、边界、证据和恢复能力的工作层。

更口语一点说：它让 Codex 不只靠聊天记忆工作。

普通聊天、解释和只读探索不需要进入复杂流程；但一旦涉及真实修改、长期跟踪、验证完成、外部环境、权限、安全、部署、归档或未来恢复，Workbench 就用结构化状态和 CLI 门禁把事情说清楚、留得住、查得回、可验证。

## 它为什么存在

Codex 做工程工作时，经常会遇到这些问题：

- 长对话压缩后，前面的边界和判断丢失。
- 用户同时有多个需求、多个任务、多个服务，Codex 容易接错对象。
- 业务代码在别的目录，当前聊天里只有片段线索。
- Codex 做了验证，但隔天说不清跑过什么。
- 用户说“可以了”，但这句话到底是任务验收、需求关闭，还是允许归档，并不总是清楚。
- AI 推断、材料摘要、测试计划、命令输出、人工确认混在一起，事实层级变乱。
- 小修改可以很轻，但高影响操作不能靠猜。

Workbench 的设计不是把每件事都变成流程，而是把会影响未来判断的东西放到合适的位置：

- 需求和任务放在 `docs/active/`。
- 服务登记放在 `services/registry.yaml`。
- 环境资料放在 `environments/`。
- 验证事实放在 evidence。
- 当前导航视图放在 `CURRENT.md` 和 `docs/generated/`。
- 完成后的冷历史放在 `docs/archive/`。
- 可复用经验放在 `docs/reusable/`。

这样新窗口、新一天、另一个 Codex 或用户自己都能重新读回真实现场。

## 三个角色

Workbench 的协作模型很简单：

| 角色 | 责任 |
| --- | --- |
| 用户 | 决定目标、范围、风险接受、验收、关闭和归档授权。 |
| Codex | 调查、实现、验证、解释，并在事实不稳或风险变大时提醒用户。 |
| Workbench | 保存现场、边界、证据、服务索引、环境资料、恢复视图和历史。 |

Workbench 不替用户做最终决策，也不自动授权 Codex 修改业务代码。它只是让决策、执行和证据之间有清楚的分层。

## 它不是什么

理解 Workbench，也要先排除几个误解：

- 它不是业务代码仓库。业务项目可以放在任何固定目录。
- 它不是 issue 系统。它不负责管理团队任务流转。
- 它不是万能自动化平台。自动化只是其中一个使用场景。
- 它不是让 Codex 每次都写状态的理由。
- 它不是让 `service_refs` 变成修改权限的白名单。
- 它不是让 generated views 覆盖 YAML 真源的入口。
- 它不是用 `doctor clean` 替代验证证据的工具。

它真正想守住的是：事实、边界、验证、恢复和可回滚的协作秩序。

## 核心设计原则

### 先理解，再执行

Codex 先判断用户真实意图，而不是机械执行字面动作词。

用户说“看看”“分析一下”“是否合理”，默认是讨论或只读探索。Codex 可以读文件和运行只读命令，但不为了留痕而写状态。

用户明确说“纳入 Workbench”“创建任务”“修复”“更新”“记录验证”“关闭”“归档”，才进入对应写入路径。

### 默认轻量

Workbench 反对空仪式。普通讨论、一次性解释、小范围只读探索和低风险小修，不应该被强行变成厚任务包。

轻量不是没有规则，而是只显性化必要信息。小修要能本地验证、可回滚、影响清楚；正式任务则需要目标、范围、风险、验证和交接闭环。

### 高影响不猜

涉及真实数据、共享环境、生产环境、权限、安全、部署、费用、通知、不可逆操作或影响他人时，Codex 必须暂停确认授权、目标、环境、回滚和验证方式。

风险判断看真实后果，不看组件名：

```text
risk = f(action, environment, blast_radius, reversibility, data_sensitivity)
```

不能写成：

```text
risk = f(component_name)
```

SQL、Redis、MQ、Docker、配置和脚本只是线索。真正决定风险的是做什么、在哪里做、影响谁、能不能恢复、能不能验证。

### 状态写入走 CLI

生命周期状态、阶段推进、验证结论、服务登记、归档和生成视图，优先走 `codex-workbench` CLI。

手改 Markdown 可以用于解释层文档，但不能手动绕过 YAML、evidence、validation、handoff、archive 等机器真源。

### 证据优先

没有 evidence，不声称“已验证”或“已完成”。

测试计划、AI 判断、`doctor clean`、`task check`、generated view、action note 和口头感觉都不能替代任务 evidence。

### 可恢复

工作台里的每个结构都在回答一个恢复问题：

- 用户目标是什么？
- 当前任务到哪一步了？
- 哪些事实确认过，哪些只是推断？
- 可以改哪些范围，什么情况要停？
- 关联哪些服务？
- 做过什么验证？
- 用户是否验收？
- 后续谁接手时该先看哪里？

## 工作空间分层

Workbench 通过多层文件协作，每层职责不同。

| 层 | 位置 | 作用 |
| --- | --- | --- |
| 人类入口 | `README.md` | 安装、启用和日常使用说明。 |
| AI 热路径 | `AGENTS.md` | Codex 每次进入时的路由卡，保留高频规则和红线。 |
| 场景手册 | `.agents/skills/workbench-*` | 不同场景的操作指南，例如恢复、任务、验证、环境、归档。 |
| 冷路径规则 | `docs/policies/` | 风险、阶段、模型、材料、服务、并发和协作等完整规则。 |
| 轻提醒 | `.codex/hooks.json` 和 `.codex/hooks/` | 向 Codex 注入简短提醒，不写状态、不推进阶段。 |
| CLI 和 schema | `src/codex_workbench/` | 状态写入、门禁、生成视图、doctor、archive、service context。 |
| 状态包 | `docs/active/` | 活动 requirement、task、evidence 等机器真源。 |
| 生成视图 | `CURRENT.md`、`docs/generated/` | 可重建导航视图，只帮助定位。 |
| 服务登记 | `services/registry.yaml` | 服务名、路径和用途索引。 |
| 环境资料 | `environments/` | 服务器、数据库、账号、部署、联调等自由 Markdown。 |
| 说明和材料 | `docs/briefs/`、`docs/materials/` | 解释型文档和原始材料副本。 |
| 可复用经验 | `docs/reusable/` | 给未来 Codex 快速复用的经验入口。 |
| 冷历史 | `docs/archive/` | 已关闭并授权归档的版本化历史。 |

这个分层的关键是：不同文件能说不同类型的话，低层级内容不能覆盖高层级事实。

## 真源模型

Workbench 最重要的概念之一是“真源”。谁能决定事实，谁只是导航或解释，必须分清。

机器状态以 YAML 为准：

- `docs/active/*/*.yaml` 是 requirement、task、evidence 等状态真源。
- `services/registry.yaml` 是服务登记真源。
- `environments/` 是环境资料输入。
- Markdown 主要负责解释给人和 Codex 看。
- `CURRENT.md` 和 `docs/generated/` 是生成视图，可重建，不是真源。

常用事实层级是：

```text
人工明确确认 / 命令输出 / 真实文件状态
> evidence
> action note
> requirement/task YAML
> discovery
> generated view
> task next_step
> AI 推断
> 未确认假设
```

这意味着：

- 用户明确确认优先于 AI 推断。
- 命令实际输出优先于计划。
- evidence 优先于 action note。
- generated view 只能帮助定位，不能覆盖 YAML。
- `task.yaml.next_step` 是恢复提示，不是完成事实。

## 请求如何分流

Workbench 先按用户意图分流，不急着写状态。

| 类型 | 典型表达 | 默认做法 |
| --- | --- | --- |
| discussion | “你怎么看”“是否合理”“解释一下” | 只讨论，不写状态。 |
| read_only_exploration | “看看代码”“查一下配置”“定位问题” | 只读调查，通常不落档。 |
| small-fix | “这个小问题直接修一下” | 明确低风险后最小修改和验证。 |
| maintenance_action | “维护 Workbench 文档/CLI/规则” | 可轻量修改本仓库，不强制正式任务。 |
| product_task | “这个需求要实现/修复/调整” | 进入 material、discovery、intake、task、evidence 流。 |
| ops_action | “登服务器、改配置、部署、跑 SQL” | 先确认环境、授权、回滚和风险。 |
| archive_action | “关闭需求”“归档版本” | 关闭和归档授权分开处理。 |

这个分流避免两种极端：

- 每次聊天都创建任务，流程膨胀。
- 真正高影响的修改没有边界、没有证据、没有恢复路径。

## 需求如何变成任务

正式产品任务不能直接从聊天或 AI 推断开始。它需要一条从原始材料到用户确认需求的路径。

典型路径是：

```text
material -> discovery -> intake -> readable requirement -> task
```

### material

`material` 只证明“收到过这个输入”。它可以是用户口述、截图、会议纪要、接口片段、文件摘要等。它不证明需求已经确认。

### discovery

`discovery` 记录只读探索结果，区分：

- confirmed facts
- system observations
- AI inferences
- assumptions
- questions for user

AI 推断不能写成确认事实。

### intake

`intake` 把材料和 discovery 整理成 AI-readable 的需求草案。它通常包含目标、验收、非目标、待确认点。

### readable requirement

只有用户确认后，requirement 才能成为 readable。正式 task 必须来自 readable requirement，除非是明确低风险的 micro 快照任务。

这个设计是为了防止“AI 看懂了大概意思”被误当成“用户确认了需求边界”。

## task 是执行界面

Requirement 表达目标和边界，task 才是执行界面。

一个 task 应该回答：

- 用户目标是什么。
- 完成口径是什么。
- 范围和非范围是什么。
- 当前阶段是什么。
- 关联哪些服务。
- 进入实现前缺什么。
- 风险等级和流程档位是什么。
- 什么情况需要暂停确认。
- 验证方式是什么。
- 交接状态是什么。

task 的主阶段只有这些：

```text
draft | ready | in_progress | verification_pending | blocked | done | obsolete
```

`review`、`implementation`、`validation`、`handoff`、`risk_level` 和 `process_level` 是维度，不是主阶段。

## implementation-ready

正式 task 修改目标内文件前，不能只靠“用户说可以改”。还要满足 implementation-ready：

- task 可以推进到 `in_progress`。
- `implementation.ready=true`。
- `implementation.conclusion=scoped`。
- `working_scope` 有真实内容。
- 验证方式清楚。
- 回滚思路清楚。
- `risk_triggers` 写清需要暂停确认的情况。
- 高风险或 critical 任务有独立复核、implementation ref、风险接受和更完整的影响画像。

`task check --to in_progress` 只是只读预演，`task set-stage --stage in_progress` 才真正写阶段。

## evidence、validation、handoff

Workbench 把“验证事实”“验证判断”和“用户交接”拆成三个概念。

### evidence

Evidence 记录已经发生的验证事实，例如：

- 哪个测试命令跑过。
- 构建是否通过。
- 哪个只读检查有明确输出。
- 用户明确完成了验收。
- 外部环境验证有什么命令、日志或人工确认支撑。

Evidence 不记录计划，也不记录 AI 自信。

### validation

Validation 是基于 evidence 的判断。它回答：这些 evidence 是否足以说明当前 task 通过验证。

`passed` 不能带未验证项。

### handoff

Handoff 是用户验收和交接维度。它可以是：

- `not_required`
- `waiting_user_validation`
- `accepted`
- `rejected`

`waiting_user_validation` 表示等待用户或外部环境反馈，不是 blocked。`accepted` 必须有 note，`rejected` 不能 done。

### done 门禁

task 能进入 `done`，必须同时满足：

- validation 是 `passed`。
- validation 有 evidence_ref。
- evidence 真实存在并属于当前 task。
- 没有 unverified_items。
- handoff 不等待、不拒绝。
- 如果 handoff accepted，必须有 note。

## close 和 archive

Workbench 特意把三件事分开：

| 动作 | 含义 |
| --- | --- |
| task done | 某个执行任务已经验证和交接闭环。 |
| requirement close | 用户确认这个需求整体关闭。 |
| archive authorization | 用户明确授权把关闭后的需求移动到冷历史。 |

用户验收任务，不等于需求关闭。需求关闭，也不等于允许归档。

归档前还要检查 requirement 下的 task 都是 `done` 或 `obsolete`，done task 有 evidence、validation 和 handoff，obsolete task 有原因。

## 风险和流程档位

Workbench 用两个概念表达任务强度：

- `risk_level`：真实后果风险。
- `process_level`：流程显性化强度。

`risk_level` 可是：

```text
low | standard | high | critical
```

`process_level` 可是：

```text
micro | lightweight | standard | high | critical
```

轻量路径只减少仪式，不降低安全语义。`micro` 和 `lightweight` 也不能跳过目标、范围、验证和交接。

`impact_profile` 用来解释风险判断，常见字段包括：

- action
- component_signals
- environment
- data_effect
- external_effect
- blast_radius
- reversibility
- contract_change
- security_or_permission
- verification_confidence

如果环境、授权、验证、回滚、权限、安全、真实数据或外部影响不清，就不能硬往下做。

## 服务登记

业务项目不需要放进 Workbench 仓库。Workbench 通过 `services/registry.yaml` 保存服务名、路径、用途和备注。

服务登记的作用是：

- 让 Codex 能通过服务名恢复本地路径。
- 让 task 标记相关服务。
- 让 generated views 和 task context 显示上下文。
- 让 Codex 在新窗口里知道该先看哪些服务。

但 `service_refs` 不是：

- 修改白名单。
- 授权证明。
- Git 分支管理工具。
- 服务仓库生命周期管理器。

是否能修改某个服务，取决于用户授权、task 阶段、working_scope、风险边界、服务真实状态和项目自身规则。

## 环境资料

`environments/` 是自由 Markdown 目录，用来保存测试环境、服务器、数据库、Redis、MQ、Nacos、GitLab、网站、账号、token、部署、联调和常用命令等资料。

它不由 schema 接管，因为真实环境资料通常不整齐。

规则是：

- 只读查看环境资料不等于授权修改外部环境。
- 信息缺失时不要猜地址、账号、库名、namespace 或 token。
- 涉及外部持久变更，要先确认授权、目标、环境、回滚和风险。
- 对外回复和 evidence 里不要复制密码、token、cookie、完整连接串或含密日志。

## CLI 的职责

CLI 是 Workbench 的状态写入器、门禁检查器和轻量上下文入口。

常见命令组包括：

- `workspace`
- `service`
- `material`
- `discovery`
- `intake`
- `requirement`
- `task`
- `evidence`
- `validation`
- `handoff`
- `action`
- `change`
- `decision`
- `suspicion`
- `index`
- `doctor`
- `archive`
- `reusable-memory`

日常入口通常是：

```powershell
codex-workbench workspace context --workspace-root .
codex-workbench task context <任务名或ID> --workspace-root .
codex-workbench service context <服务名> --workspace-root .
```

阶段推进前用：

```powershell
codex-workbench task check <任务名或ID> --to in_progress
codex-workbench task set-stage <任务名或ID> --stage in_progress
```

完成前用：

```powershell
codex-workbench evidence create ...
codex-workbench validation apply ...
codex-workbench handoff set ...
codex-workbench task check <任务名或ID> --to done
codex-workbench task set-stage <任务名或ID> --stage done
```

重要边界：

- `task check` 是只读预演。
- `task set-stage` 才写阶段。
- `doctor check` 是健康检查，不是 evidence。
- `index generate` 生成视图，不创造事实。
- 命令不会替用户做风险接受或验收确认。

## skills、policies 和 hooks 的关系

这三者经常被混淆。

### `AGENTS.md`

`AGENTS.md` 是热路径入口卡。它只保留高频路由、真源边界和红线，让 Codex 进入仓库时先拿到正确姿势。

它不承载所有细节。

### skills

`.agents/skills/workbench-*` 是场景手册。它们告诉 Codex：

- 当前请求属于什么场景。
- 应该先读哪里。
- 什么时候用 CLI。
- 什么时候停下来确认。
- 哪些反例不能做。

现有 skill 大致分工：

| skill | 作用 |
| --- | --- |
| `workbench-resume` | 恢复现场、选择工作对象、处理模糊指代。 |
| `workbench-cli` | 查命令、核对参数、区分 CLI 写入边界。 |
| `workbench-task` | 判断任务类型、创建或准备 requirement/task、小修和维护分类。 |
| `workbench-gate-check` | 阶段推进前只读自检。 |
| `workbench-evidence` | 记录 evidence、validation、handoff，判断 done。 |
| `workbench-environment` | 环境资料、外部系统、账号、部署和敏感操作边界。 |
| `workbench-archive` | requirement close、archive preflight、archive version 和历史查询。 |

### policies

`docs/policies/` 是冷路径规则。它们给 CLI、doctor、测试和复杂判断提供完整语义。

Codex 不需要每次聊天都全读 policies；只有涉及风险、阶段、写状态、验证、环境、归档或歧义时才展开。

### hooks

`.codex/hooks.json` 和 `.codex/hooks/` 只注入轻提醒，例如：

- 聊天和只读探索不写状态。
- 需要写状态、evidence、环境、完成或风险判断时再展开规则。
- generated views 只导航，YAML、registry、evidence、文件和命令输出决定事实。

Hook 不写状态，不运行 doctor，不推进阶段，也不归档。

## generated views 的作用

`CURRENT.md`、`docs/generated/index.md` 和 `docs/generated/recovery.md` 是导航视图。

它们适合：

- 新窗口快速知道当前有没有活动任务。
- 多任务时定位候选对象。
- 查看等待反馈、阻塞、最近 evidence 或异常。
- 发现 generated view stale 或引用冲突。

它们不适合：

- 代替 task YAML。
- 代替 evidence。
- 覆盖 requirement 的确认状态。
- 作为唯一工作对象锁。
- 手工编辑。

如果 generated view 和 YAML 冲突，回到 YAML、evidence、registry、命令输出和用户确认。

## 可复用经验和自动化

`docs/reusable/` 保存给未来 Codex 复用的经验，分成：

- workflow
- services
- validation
- architecture
- environment
- patterns
- pitfalls

白天 Codex 可以用 `codex-workbench reusable-memory find/get` 查这些经验。但 reusable memory 只是入口，不是真源。

早间或夜间自动化可以维护这些文件，但自动化边界非常窄：

- 只允许维护 `docs/reusable/*.md`。
- 只允许维护自动化 handoff 和月度 SQLite ledger。
- 不改业务代码。
- 不改 task 包。
- 不改 policy、skill、AGENTS、环境资料或 generated views。
- 不写秘密值。
- 不为了有产出而硬新增记忆。

这个设计让“沉淀经验”和“当前工作状态”分离。白天 Codex 读到的是干净经验，夜间维护日志留在自动化私有 ledger 中。

## 测试和工程实现思路

Workbench 的实现不是只靠文档约定，它也通过 Python CLI 和测试把很多规则固化下来。

技术上：

- Python 3.11+。
- Typer 作为 CLI 框架。
- Pydantic v2 做严格模型校验。
- YAML 做机器状态。
- Markdown 做解释层。
- 写文件使用 UTF-8、原子替换和路径约束。
- package 创建和归档有失败回滚设计。

测试覆盖：

- schema 严格性。
- lifecycle guard。
- CLI 命令。
- service context。
- generated index。
- doctor。
- archive preflight。
- reusable memory。
- hooks。
- 从 material 到 archive 的端到端 dogfood 流程。

所以 Workbench 不是一堆模板，而是一个带 guard 的本地状态机。

## 新人如何开始使用

如果你第一次用，可以按这个心智模型来：

### 只是问问题

直接问，不需要创建任务。

```text
你帮我看看这个方案有没有风险，先讨论，不写状态。
```

### 想了解一个服务

先只读探索。

```text
先了解 user-api 的认证模块，不要改代码，帮我说清入口和风险。
```

### 想做一个小修

说明影响小、允许修改，并要求验证。

```text
这个展示文案写错了，影响很小，直接帮我修一下并跑相关验证。
```

如果 Codex 调查后发现影响变大，它应该停下来说明。

### 想正式纳入需求

先让 Codex 整理材料和待确认点，不急着写代码。

```text
这个需求要纳入 Workbench。先整理材料、目标、验收、非目标和待确认问题，不要直接实现。
```

### 想继续旧任务

让 Codex 先恢复现场。

```text
继续上次那个任务，先告诉我现在到哪了、能不能继续改。
```

### 你验收通过了

明确说这是验收。

```text
我验收通过了，帮我收尾，检查能不能标记 done。
```

Codex 应该补 evidence、validation、handoff，再用 gate-check 判断。

### 想关闭和归档

分开说。

```text
这个需求可以关闭。
```

```text
我授权把这个需求归档成一个版本。
```

## 常见误解

### “README 已经说清楚了，为什么还要这份文档？”

README 是安装和上手入口。这份文档解释设计思想、状态语义和为什么这么做。两者定位不同。

### “CURRENT.md 里没有任务，是不是没有工作可做？”

不一定。`CURRENT.md` 是有限的生成视图，不是完整真源。需要完整目录时看 `docs/generated/index.md`，需要任务事实时看 task 包。

### “service_refs 写了某服务，是不是可以改这个服务？”

不是。`service_refs` 只是上下文索引。修改授权来自用户请求、task stage、working_scope、风险边界和真实服务现场。

### “task check 通过，是不是已经进入阶段？”

不是。`task check` 是只读预演。写阶段要用 `task set-stage`。

### “doctor clean 是不是证明任务完成？”

不是。`doctor clean` 只说明工作区硬健康检查通过，不能替代任务验证 evidence。

### “用户说可以了，是不是就能 done？”

要看“可以了”的含义。可能是继续推进、可能是验收、可能只是暂时认可方案。done 需要 evidence、validation 和 handoff 闭环。

### “需求关闭是不是自动归档？”

不是。Requirement close 和 archive authorization 是两个独立用户确认。

### “自动化会不会帮我维护一切？”

不会。可复用经验自动化只维护很窄的资料范围，不改业务代码、不改 task 包、不改 policy 和环境资料。

### “子代理说没问题，是不是事实？”

不是。子代理适合复核、并行检查和风险扫描，但它的结论不是状态真源。主 Codex 仍要核对文件、命令输出和状态包。

## 朋友应该先读哪些文件

推荐顺序：

1. `README.md`：知道 Workbench 是什么，怎么安装和启用。
2. 本文档：理解设计思想和术语。
3. `AGENTS.md`：看 Codex 每次进入时如何路由。
4. `WORKSPACE.md`：理解目录职责。
5. `.agents/skills/workbench-resume/SKILL.md`：理解恢复现场和工作对象选择。
6. `docs/policies/action-routing.md`：理解请求如何分流。
7. `docs/policies/state-and-gates.md`：理解阶段、evidence、done、close、archive。
8. `docs/policies/risk-and-process.md`：理解风险判断。
9. `src/codex_workbench/models.py` 和 `src/codex_workbench/lifecycle.py`：如果想看实现真相。

不用一开始读完整个仓库。Workbench 的思想是按需展开：热路径少，冷路径全；先接住用户要做什么，再决定读多深。

## 最后再压缩成一句

Workbench 不是让 Codex 变慢的流程，而是让 Codex 在该轻的时候轻、该稳的时候稳：聊天不落档，小修不膨胀，正式任务有边界，高风险先确认，完成必须有证据，历史可以恢复。
