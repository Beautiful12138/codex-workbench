# Codex Workbench 入口卡

本文件是每次进入 Workbench 时读取的热路径路由卡，只保留启动姿势、真源边界和红线。具体动作按匹配的 `workbench-*` skill 展开；完整规则在 `docs/policies/`。

`codex-workbench` 是个人本地多项目工程协作工作台，用于让 Codex 在多个需求、多个任务、多个服务之间稳定工作。

## 协作原则

尊重式纠错：用户可能错了不意味着不尊重用户。若用户前提与真实文件、命令输出、YAML 真源、evidence、policy 或风险边界冲突，应简短呈现证据并选择更稳的路径；不呈现证据、顺着错误前提继续，才是不尊重。

## 进入时

先接住用户要做什么：聊天、只读探索、小修、正式任务、环境操作、验证完成、还是归档。先看现场，再决定要不要展开 skill、policy 和包细节。

1. Workbench CLI 必须来自用户 Python 环境中已安装的 `codex-workbench` 命令；命令不可用时先修复安装或 PATH，不要临时绕过。
2. 优先运行 `codex-workbench workspace context --workspace-root .`。
3. 选中 task 后先用 `task context <任务名或ID>`；涉及服务先用 `service context <服务名>`。
4. 只有需要写状态、看细节或处理门禁时，再读对应 YAML、Markdown、policy、skill、`services/registry.yaml`、`environments/` 或 `docs/archive/`。
5. 普通讨论、解释和只读探索，不为了留痕而写状态。

默认路径：`workspace context -> task context -> service context -> task package`。生成视图只用于定位和恢复，不能覆盖包 YAML 真源。

`workspace context` 的项目概览只全量展示服务名称；路径、Git 和入口等详情仍按需进入 `service context`。

## Skill 入口

按用户意图使用匹配的 skill；skill description 是场景发现入口，进入具体场景后再读本仓库内对应路径的 `SKILL.md`，不要去用户业务项目路径下寻找 Workbench skill。

- 当前状态、继续、模糊指代、选择对象、读取深度：`.agents/skills/workbench-resume/SKILL.md`
- CLI 命令、参数、`--help`、context、index/doctor/generated views、写状态命令边界：`.agents/skills/workbench-cli/SKILL.md`
- 新需求、材料、任务、小修、维护、风险画像、准备实现：`.agents/skills/workbench-task/SKILL.md`
- 阶段推进、门禁预演、`task check`、`set-stage`、blocked、obsolete：`.agents/skills/workbench-gate-check/SKILL.md`
- evidence、validation、handoff、用户验收、done 判断：`.agents/skills/workbench-evidence/SKILL.md`
- 环境、服务器、数据库、账号、token、部署、日志、外部系统：`.agents/skills/workbench-environment/SKILL.md`
- 关闭需求、归档、版本、历史：`.agents/skills/workbench-archive/SKILL.md`

## 可复用记忆

只在当前任务可能复用历史经验时使用 `codex-workbench reusable-memory find/get`；必要时再打开对应 `docs/reusable/` 维度文件兜底查看。`docs/reusable/` 是派生记忆入口，不是事实真源；高风险、环境、部署、数据、权限或事实冲突时，回到当前代码、环境资料、policy 和真实命令输出核验。

## 工作对象

显式路径优先；名称和自然指代优先用于对用户表达；ID 用于内部精确定位。仍无法唯一判断，且继续会写状态、改文件、推进阶段或声明完成时，先问一个聚焦问题。

不要因为 `CURRENT.md` 没有某个任务就认为没有可推进任务；也不要因为 `CURRENT.md` 提到某个对象就忽略用户当前明确指定的对象。

## 真源

- `docs/active/*/*.yaml` 是 requirement、task、evidence 的机器状态真源；Markdown 是解释层，不覆盖 YAML。
- `services/registry.yaml` 是服务登记和只读状态输入；`environments/` 是环境资料。
- `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md` 是可重建视图，不覆盖真源。
- `docs/archive/` 是版本化冷历史，默认不作为当前上下文。
- `docs/actions/`、`docs/changes/`、`docs/decisions/`、`docs/suspicions/` 是非任务记录真源，但不能覆盖 task/evidence。
- `docs/materials/`、`docs/briefs/` 是轻量资料入口；内容可供发现和解释，但不覆盖需求、任务、服务或验证真源。

事实证据层级：人工明确确认 / 命令输出 / 真实文件状态 > evidence > action note > requirement/task YAML > discovery > generated view > task next_step > AI 推断 > 未确认假设。

## 写入器选择

修改前先判断语义：状态流转、结构化关联、验证结论、归档关系和服务登记，优先走 `codex-workbench` CLI 或对应 `workbench-*` skill；解释层文档、工作产物、普通说明和低风险机械修正，可在授权范围内最小手工编辑。

当 CLI 同时创建 YAML 与 Markdown 时，命令成功只表示机器状态和正文骨架已经建立，不表示整份记录已经写完。除非用户明确只要求空骨架，Codex 应在同一轮打开同名 Markdown，根据真实现场补写足以恢复上下文的背景、过程、判断、结果和后续；事实不足时明确写出已知内容与待确认缺口，不编造，也不机械复述 YAML。留下全空章节后声称记录完成，属于未完成。

用户同意“修改内容”不等于同意绕过状态写入器。若手工编辑可能改变生命周期、范围、验证事实、恢复上下文或生成视图，先说明原因、影响和验证方式，再取得明确授权；否则改后运行相应检查。

## 红线

- 没有用户确认的 readable requirement，不创建正式产品 task。
- 正式产品 task 未进入 `in_progress` 或 implementation-ready 不清时，不修改任务目标内文件；明确授权的 `small-fix` / `maintenance_action` 只能按低风险、可验证、可回滚的边界最小执行。
- `service_refs` 是相关服务标记，不是修改白名单。
- 涉及状态/索引语义时，用户同意改内容不等于同意绕过 CLI/skill；手工编辑需先说明原因、影响和验证方式。
- 涉及环境、账号、数据、部署、安全、权限、费用、不可逆操作、影响他人或共享环境时，先确认授权和风险边界。
- 没有 evidence，不声称已验证或已完成。
- action note、doctor clean、测试计划、gate-check、口头判断都不能替代 task evidence。
- 用户验收、task done、requirement close、archive authorization 不能互相替代。

## Policy 地图

动作分流看 `docs/policies/action-routing.md`；风险看 `docs/policies/risk-and-process.md`；恢复和并发看 `docs/policies/recovery-and-concurrency.md`；状态门禁看 `docs/policies/state-and-gates.md`；服务环境看 `docs/policies/services-and-environment.md`；材料看 `docs/policies/materials.md`；模型真源看 `docs/policies/model-schema.md`；协作看 `docs/policies/agent-coordination.md`。

`.codex/hooks.json` 只提供轻量提醒，不写状态、不运行 doctor、不推进阶段、不归档。`doctor check` 是只读健康检查，不能替代 evidence、用户验收或风险接受。
