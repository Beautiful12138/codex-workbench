---
name: workbench-resume
description: Use when Codex 需要恢复 codex-workbench 现场、回答当前状态/下一步/有哪些任务、处理“继续/刚才那个/当前需求”等模糊指代、选择工作对象、普通讨论/只读探索入口或决定读取深度。
---

# Workbench Resume

## 适用场景

使用本 skill 处理：

- 新窗口进入 `codex-workbench`。
- 用户问“当前状态”“接下来做什么”“有哪些任务”。
- 用户给出模糊指代，例如“继续那个任务”“看一下当前需求”。
- 需要在多个 requirement、多个 active task、多个 service 中选择工作对象。
- 用户提到环境、服务器、数据库、GitLab、网站、联调、账号密码或操作方式。
- 需要决定是只读探索、写 discovery、推进 task，还是暂停确认。

## 核心原则

恢复现场不是跑流程，而是先把用户当前问题接住：他是在问状态、找任务、继续实现、反馈测试结果，还是只想讨论一个方向。先用 `workspace context` 看轻量现场；只在事情要落到状态、代码、环境、验证或归档时再加深。

`AGENTS.md` 是稳定入口规则卡。`CURRENT.md`、`docs/generated/recovery.md` 和 `docs/generated/index.md` 是辅助定位的 generated views，不是完整手册，也不作为单任务锁。工作对象选择必须来自用户请求、显式路径、名称、ID、这些 generated views 或包 YAML。

名称优先：用户通常不会记 task id / requirement id。ID 是内部锚点，对用户回复默认不向用户暴露；只有歧义、调试、复制命令或用户明确要求时才说 ID。

generated views 是索引，不是真源。判断阶段、范围、验证和交接时，以包 YAML、evidence 和用户确认为准。

高风险、unknown、真实后果、done 或归档场景，不能只凭 `workspace context`、`task context` 或 generated views 摘要行动；必须回到 task YAML、`docs/policies/risk-and-process.md`、evidence / validation / handoff 和 CLI 门禁输出。

等待反馈是正常接续状态，不是阻塞。`verification_pending` 或 `handoff.status=waiting_user_validation` 表示工作已交给用户、测试环境或外部系统确认；默认轻量展示，用户反馈“测过了/可以关掉”时再按名称、服务或最近等待项定位并补录 evidence / validation / handoff。

## 读取顺序

先按读取深度走，不要一开始展开所有材料：

1. 读 `AGENTS.md`，拿到入口地图。
2. 运行 `workspace context --workspace-root .`，先看轻量现场。
3. 用户给出显式路径、需求/任务名称、REQ/TASK ID、服务名时，优先读取对应对象。
4. 仍不清楚对象时，再读 `CURRENT.md`、`docs/generated/recovery.md`；需要完整活动目录时才读 `docs/generated/index.md`。
5. 选择到 task 后，优先运行 `task context <任务名或ID>` 看当前能做什么、缺什么；需要细节时再读 `docs/active/<TASK-ID>/task.yaml` 和 `task.md`。
6. 涉及服务时，优先运行 `service context <服务名>`；需要完整登记时再读 `services/registry.yaml`。
7. 涉及环境、服务器、数据库、GitLab、网站、联调、账号密码或操作方式时，查 `environments/` 中相关 Markdown。
8. 涉及验证、done、归档、高风险、unknown 或真实后果时，再读 evidence、handoff、policy、review / implementation 信息。

默认路径：workspace context -> task context -> service context -> task package。

## 工作对象选择

按以下顺序选择：

1. 显式路径优先。
2. 名称优先于 ID 展示；内部用 ID 找包，回复用户默认说名称。
3. 显式 ID 优先于语义推断。
4. 用户语义匹配时，用 recovery 和包 YAML 对齐。
5. 多个 active task 都可能匹配时，优先选择用户最近明确提到的对象。
6. 无法唯一判断且继续会写状态或改文件时，用名称、阶段、服务和最近更新时间让用户选择。

如果只是普通讨论或只读探索，可以继续调查，不必立刻要求用户选择任务。

## 空工作台行为

当 workspace 是 baseline，且没有 active requirement/task 时，先判断用户是在聊天、探索、提出新需求、要求维护本仓库，还是要求纳入 Workbench 流程。

- 用户只是问状态：只读回答，不写状态。
- 用户提出新需求：引导 material / discovery / intake，不直接创建 task。
- 用户要求修改 codex-workbench 自身：走 `maintenance_action` / repo maintenance，不强制创建 requirement/task。
- 用户明确授权小型低风险修改：按风险公式确认影响清楚、可回滚、可验证后，走 `small-fix` 最小改动和最小验证。
- 用户要求把这次工作纳入 Workbench 流程：再创建 requirement/task。
- 用户问下一步：给出 2-3 个可选入口，不主动创建任务。

回答“下一步做什么”时，先给用户能选择的入口。如果下一步真的会写状态、推进阶段、生成视图、检查状态或归档，再读 `workbench-cli` 并用 `--help` 核对命令。

## 状态回答格式

回答当前状态时，优先让用户一眼知道三件事：

- 现在是什么工作面：baseline、活动需求/任务、等待反馈、阻塞、风险缺口或服务缺口。
- 当前能做什么：只读探索、继续某个任务、补 evidence、等待用户反馈、登记服务或创建需求。
- 当前先别做什么：不能写状态、不能推进、不能声明 done、不能碰外部环境，或者需要先确认对象。

涉及任务时用需求/任务名称说话；ID 只在歧义、调试、复制 CLI 命令或用户明确要求时出现。

不要把 archive 历史默认展开到当前状态；用户问历史时再查。

## 停止点

遇到以下情况停止推进：

- 工作对象无法唯一判断，但继续会写状态、改文件或推进阶段。
- 目标、范围、验收、服务关系或确认口径不清。
- 触发当前 task 的 `risk_triggers`。
- 要修改外部服务目录、外部环境、真实数据或 Git 状态，但授权或环境资料不清。
- 用户只是讨论方向，而你必须写状态才能继续。

## 常见反例

- 不要因为 `CURRENT.md` 没有 current_task 就说没有工作可做。
- 不要因为 recovery 里有第一个 active task 就自动选择它。
- 不要用 generated view 覆盖包 YAML。
- 不要把旧聊天摘要当成高层级事实。
- 不要为了恢复现场全量读取 archive。

## 常用命令

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench workspace context --workspace-root .
python -m codex_workbench task context <TASK-NAME-OR-ID> --workspace-root .
python -m codex_workbench service context <SERVICE-NAME> --workspace-root .

# 怀疑生成视图或工作区健康异常时再用：
python -m codex_workbench index check --workspace-root .
python -m codex_workbench doctor check --workspace-root .
```
