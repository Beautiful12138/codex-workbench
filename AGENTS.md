# Codex Workbench 入口地图

本文件是每次进入 Workbench 时读取的最小路由卡。它帮助 Codex 先接住用户要做什么，再决定要不要展开规则、skill 和包细节。完整规则在 policy 和 skill 中。

`codex-workbench` 是个人本地多项目工程协作工作台，用于让 Codex 在多个需求、多个任务、多个服务之间稳定工作。

## 进入时

先接住用户要做什么：是在聊天、只读探索、小修、推进正式任务，还是涉及环境/数据/部署。先看现场，再决定要不要展开规则。

1. 读 `AGENTS.md`。
2. 在本源码仓库运行 CLI 前设置 `$env:PYTHONPATH='src'`，再优先运行 `python -m codex_workbench workspace context --workspace-root .`。
3. 结合用户明确给出的路径、需求/任务名称、ID、服务名或环境资料，判断当前工作对象。
4. 选中 task 后先用 `task context <任务名或ID>`；涉及服务先用 `service context <服务名>`。
5. 只有需要写状态、看细节或处理门禁时，再读对应 requirement / task 包 YAML、Markdown、policy、skill、`services/registry.yaml`、`environments/` 或 `docs/archive/`。

默认路径：workspace context -> task context -> service context -> task package。`workspace context` 默认只做轻量服务概览，不深扫服务路径/Git；需要服务现场时再点名 `service context <服务名>` 或显式 `workspace context --check-services`。普通讨论、解释和只读探索，不为了留痕而写状态。生成视图只用于定位和恢复，不能覆盖包 YAML 真源。

## 协作判断

尊重用户目标，但先校验再配合。用户方向、判断、方案和风险结论不自动等于事实正确或路径最优。

执行前多思考一步：用真实文件、命令输出、YAML 真源、项目规则和风险公式核对事实、目标、影响和风险。若方向成立，说明依据后执行；若不成立或不完整，简短指出问题并给出更稳路径。

## 需要展开的场景

- 要写状态、推进阶段、生成视图、检查状态、归档，或不确定 CLI 怎么做：读 `workbench-cli`，执行前用 `python -m codex_workbench <group> <command> --help` 核对。
- 空工作台、baseline、没有 active requirement/task、用户问下一步：读 `workbench-resume`；只给可选入口，不主动创建任务。
- 用户明确要求修改 codex-workbench 自身、维护本仓库、调整规则/skill/CLI/测试：默认走 `maintenance_action` / repo maintenance；不强制创建 requirement/task。
- 用户明确授权的小型低风险修改：先按风险公式判断；影响清楚、可本地验证、可回滚时走 `small-fix`，不自动创建正式 task。
- 继续、当前状态、有哪些任务、模糊指代、多个 active task 选择：读 `workbench-resume`。
- 新需求、材料、创建任务、推进阶段、风险画像、改代码或修复问题：读 `workbench-task`；选中 task 后先看 `task context`，再按场景读 action/risk/state policy。
- 阶段推进前、task check、set-stage、in_progress、done、blocked、obsolete：读 `workbench-gate-check` 做只读自检，再按结果决定是否执行 CLI。
- DB、SQL、Redis、MQ、配置、部署、权限、真实数据、生产/共享环境、不可逆或影响他人：读 `docs/policies/risk-and-process.md`，必要时暂停确认。
- 服务器、数据库、GitLab、网站、账号密码、token、联调、日志、部署或外部系统操作方式：读 `workbench-environment` 和 `environments/`。
- 验证、通过、完成、done、交付、验收、handoff：读 `workbench-evidence` 和 task evidence/validation/handoff。
- 关闭需求、归档、版本、历史：读 `workbench-archive`。

## 按场景读取

- 判断请求入口模式时，先按 `chat`、`explore`、`small-fix`、`formal-task`、`ops-action`、`archive` 分流，再决定是否写状态。
- 恢复现场、回答状态、选择工作对象、处理模糊指代：使用 `workbench-resume`，先看 `workspace context`；需要更完整目录时再读 `CURRENT.md`、`docs/generated/recovery.md` 或 `docs/generated/index.md`。
- CLI 命令、参数、状态写入或 generated views：使用 `workbench-cli`，读本 skill 并用 `--help` 核对。
- 创建需求、推进任务、调整风险画像或阶段：使用 `workbench-task`；选中 task 后先用 `task context`，写状态、改阶段或需要细节时再读 task 包和 `docs/policies/action-routing.md`、`risk-and-process.md`、`state-and-gates.md`。
- 阶段推进、完成、阻塞、废弃或门禁预演：使用 `workbench-gate-check`，读 task/evidence/handoff 和 `docs/policies/state-and-gates.md`。
- 环境、服务器、数据库、GitLab、网站、账号密码、token、联调、部署或外部系统操作方式：使用 `workbench-environment`，读 `environments/` 和 `docs/policies/services-and-environment.md`。
- 记录验证、应用 validation、处理 handoff、判断 done：使用 `workbench-evidence`，读 task、evidence、validation 和 handoff。
- requirement close、archive preflight/version 或查询冷历史：使用 `workbench-archive`，读 requirement、task、archive policy 和 archive 包。

## 工作对象选择

1. 显式路径优先：用户给出 `docs/active/...`、任务包、需求包、环境资料或服务路径时，先读该路径。
2. 名称优先：用户通常说需求/任务名称或自然指代；对用户回复默认使用名称，ID 是内部锚点，默认不向用户暴露。
3. 显式 ID 其次：用户点名 `REQ-*`、`REQ-*-TASK-*`、`EV-*`、action/change/decision/suspicion ID 时，读取对应对象。
4. 用户语义匹配：用户说“刚才那个任务”“这个需求”“某服务的问题”时，用 recovery、index 和包 YAML 对齐。
5. 仍无法唯一判断，且继续会写状态、改文件或推进阶段时，先用名称、阶段、服务和最近更新时间问一个聚焦问题。

不要因为 `CURRENT.md` 没有某个任务就认为没有可推进任务；也不要因为 `CURRENT.md` 提到某个对象就忽略用户当前明确指定的对象。

## 状态真源

- `docs/active/*/*.yaml`：requirement、task、evidence 的机器状态真源。
- `docs/active/*/*.md`：给人和 Codex 的解释层，不覆盖 YAML。
- `services/registry.yaml`：服务登记和只读状态输入。
- `environments/*.md`：本地环境资料、服务器、数据库、GitLab、网站、账号密码和操作方式；自由 Markdown，不由 CLI/schema 接管。
- `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md`：可重建视图，不覆盖真源。
- `docs/archive/`：版本化冷历史，默认不作为当前上下文。
- `docs/actions/`、`docs/changes/`、`docs/decisions/`、`docs/suspicions/`：非任务动作、范围变化、长期决策和疑点线索。

事实层级：人工明确确认 / 命令输出 / 真实文件状态 > evidence > action note > requirement/task YAML > discovery > generated view > task next_step > AI 推断 > 未确认假设。

## 红线

- 没有用户确认的 readable requirement，不创建正式产品 task。
- 没有 `in_progress` task 和清楚 implementation-ready，不修改任务目标内文件。
- `service_refs` 是相关服务标记，不是修改白名单。
- 涉及环境、账号、数据、部署、安全、权限、费用、不可逆操作、影响他人或共享环境时，先确认授权和风险边界。
- 没有 evidence，不声称已验证或已完成。
- action note、doctor clean、测试计划、口头判断都不能替代 task evidence。

## Policy 地图

- `docs/policies/action-routing.md`：请求分流、状态写入边界和反例。
- `docs/policies/risk-and-process.md`：风险判断、影响面画像和流程档位。
- `docs/policies/recovery-and-concurrency.md`：工作对象选择、多包并发和恢复规则。
- `docs/policies/state-and-gates.md`：阶段、门禁、验证、交接、完成和归档。
- `docs/policies/materials.md`：材料、discovery、intake 和事实边界。
- `docs/policies/services-and-environment.md`：服务登记、环境资料、多服务协作和 Git 边界。
- `docs/policies/agent-coordination.md`：skills、子代理、复核和接续方式。
- `docs/policies/lifecycle-semantics.md`：生命周期语义。
- `docs/policies/model-schema.md`：核心模型和 schema 语义。

## 自动提醒与健康检查

`.codex/hooks.json` 只提供轻量提醒，不写状态、不运行 doctor、不推进阶段、不归档。`doctor check` 是只读健康检查，只报告机器真源和 lifecycle 的硬问题；它不是流程教练，不能替代人工判断、evidence、用户验收或风险接受。
