# codex-workbench

`codex-workbench` 是一个给 Codex 使用的本地工程工作台。

如果你经常让 Codex 同时处理多个需求、多个任务、多个服务，或者希望它在换窗口、长对话压缩、隔天继续时还能稳定恢复现场，这个仓库就是用来承载那张“工作台”的。

它不是业务项目，也不是 issue 系统。业务代码可以放在别的目录里，Workbench 只负责保存需求、任务、服务登记、环境资料、验证证据、归档历史和可复用经验。

## 你应该先知道什么

一个简单模型：

- 你是需求负责人：决定目标、授权风险、确认验收。
- Codex 是开发者：调查、实现、验证、解释，并在事实不稳时提醒你。
- Workbench 是工作台：保存现场、边界、证据、服务索引和历史。

Workbench 不会替你做最终决策，也不会自动授权 Codex 修改业务代码。它帮助 Codex 少靠聊天记忆硬撑，并在复杂工作里少越界。

适合使用 Workbench 的情况：

- 你有多个需求或任务需要 Codex 长期跟踪。
- 一个需求可能涉及多个本地业务仓库。
- 你希望 Codex 记录验证证据，而不是只说“应该可以了”。
- 你希望隔天、换窗口或上下文压缩后，Codex 还能恢复现场。
- 你希望已完成工作的经验能沉淀成以后可复用的材料。

不一定需要 Workbench 的情况：

- 只是一次性问答。
- 只让 Codex 看一小段代码解释。
- 一个很小、很明确、不会复用的临时修改。

这些场景也可以在 Workbench 里做，但默认不需要创建正式任务。

## 想让 Codex 代劳？

如果你已经读懂 Workbench 的用途，只是不想自己 clone、装依赖、配 PATH 和创建自动化，可以先把 `<你的 Workbench 目录>` 改成自己的本地目录，再把下面这段复制给 Codex。

```text
目标目录：<你的 Workbench 目录>
仓库地址：https://github.com/Beautiful12138/codex-workbench.git

请阅读当前 README.md，并在当前工作目录完成 codex-workbench 的安装、启用和可复用经验维护自动化配置。

如果当前还没有这个仓库，请先把仓库拉取到目标目录，再进入目标目录阅读 README.md 并继续。

不要创建正式任务，不要修改业务代码；如果需要我在界面里信任 hooks，请提醒我。
```

## 1. 安装 Workbench

安装 Workbench 的目标是：把这个仓库放在一个固定目录，并把 `codex-workbench` CLI 安装到当前用户的 Python 环境里。这样 Codex 进入这个目录后，就能用 CLI 读取工作台现场、挂载服务、记录验证和恢复上下文。

你需要提前准备两件事：

- 电脑里有可用的 Python。
- 你愿意把 Workbench 放在一个固定目录，例如 `E:\AI\codex-workbench`。

安装时应遵守这些边界：

- 如果目标目录不存在，clone 仓库到该目录。
- 如果目标目录已经存在，只检查仓库状态，不要覆盖本地改动。
- 依赖安装到当前用户 Python 环境，不创建本仓库专用环境。
- 安装后必须验证 `codex-workbench` 命令可用。

典型命令如下；如果你让 Codex 代劳，它应按这些步骤执行并根据你的系统环境调整 Python 命令：

```powershell
git clone https://github.com/Beautiful12138/codex-workbench.git <你的 Workbench 目录>
cd <你的 Workbench 目录>
python -m pip install --user -e ".[dev]"
codex-workbench version
codex-workbench workspace context --workspace-root <你的 Workbench 目录>
```

如果 Python 用户 Scripts 目录不在 PATH，需要把它加入用户 PATH。当前已经打开的 Codex Desktop 或终端可能还看不到新路径；重启 Codex Desktop，或新开一个终端后再继续使用。

Codex 安装成功后，你不需要背 Workbench 命令。以后进入这个仓库时，Codex 会根据 `AGENTS.md`、skills 和 CLI 自己展开需要的动作。

## 2. 在 Codex 中启用 Workbench

启用 Workbench 的意思是：让 Codex 在这个仓库目录里工作，并能读取本仓库的 `README.md`、`AGENTS.md`、skills、hooks 和 CLI。

在 Codex Desktop、Codex CLI 或你正在使用的 Codex 环境里，把工作目录设为你的 Workbench 目录。下面只是示例：

```text
E:\AI\codex-workbench
```

进入后，Codex 应先读取 `README.md` 和 `AGENTS.md`，再按需要展开 `.agents/skills/workbench-*` 和 CLI。你不用先背命令，也不用知道内部文件该按什么顺序读。

如果 Codex Desktop 提示需要信任本仓库的 hooks，这一步需要你在界面里确认。Codex 可以帮你解释 `.codex/hooks.json` 做了什么，但不能替你完成界面授权。当前 hooks 只是轻提醒：讨论/只读探索不写状态，改代码或声明完成前先打开任务规则和 CLI。

### 可选：创建可复用经验维护自动化

如果你希望 Workbench 在工作日自动整理可复用经验，可以在 Codex Desktop 的“已安排”里创建一个自动化。如果你让 Codex 代劳，它应按下面这张配置单创建或更新自动化。

```text
自动化名称：Workbench 夜间可复用经验维护
工作空间：<你的 Workbench 目录>
运行环境：local
模型：gpt-5.5
推理强度：xhigh
时间：每个工作日早上 07:00
时间配置要求：按 Codex Desktop 界面/本地时间直接配置为周一到周五 07:00，不要换算成 UTC 的周日到周四 23:00。
状态：启用

自动化提示词：
你是 codex-workbench 的夜间可复用经验维护 Codex。

目标：每个工作日从已完成、已验证、已归档或有新 evidence / handoff 的工作中，提炼少量未来白天 Codex 可复用的经验，并保持 docs/reusable/ 简洁、可信、不过度膨胀。

启动后必须先读取：
1. AGENTS.md
2. .codex/automations/reusable-materials/runbook.md
3. .codex/automations/reusable-materials/handoff.md

只允许维护：
- docs/reusable/*.md
- .codex/automations/reusable-materials/handoff.md
- .codex/automations/reusable-materials/ledger/YYYY-MM.sqlite

不要修改业务代码、任务包、policy、skill、AGENTS、环境资料或 generated views。读取代码、任务、归档、环境资料和 task 绑定服务时只读，用来判断知识是否仍可复用。

使用当前用户 Python 环境中已安装的 codex-workbench 命令；不要创建本仓库专用环境，也不要临时绕过已安装命令。需要维护 ledger 时，按 runbook 调用 .codex/automations/reusable-materials/reusable_ledger.py。

按 runbook 执行容量规则：每个维度 20 条以内通常不用为数量维护；达到 30 条时主动考虑压缩、合并或删除；50 条是硬上限。

完成时汇报：本次读取了哪些候选范围、新增/更新/删除/合并/跳过了什么、ledger 和 handoff 是否写入成功、是否有需要下一次接续的问题。若任何关键检查失败，不要扩大修改，按 runbook 标记 partial 或 failed。
```

创建或更新后，Codex 应读取自动化配置，确认工作空间、模型、推理强度、时间和状态都正确。已安排界面应显示“周一-周五（时间：07:00）”；如果显示“周日-周四（时间：23:00）”，说明时间配置错了，应更新为界面语义下的工作日 07:00。

## 3. 挂载你的业务服务

业务项目不需要放进这个仓库。你可以把它们 clone 到任意固定目录，然后登记到 Workbench。

例如，你有一个业务服务：

```text
E:\AI\services\user-api
```

你可以直接对 Codex 说：

```text
我有一个业务服务叫 user-api，路径是 E:\AI\services\user-api，它是用户接口服务。帮我挂到 Workbench。
```

Codex 会把它登记到 `services/registry.yaml`。之后当某个任务涉及这个服务时，Codex 可以通过服务名恢复路径、查看服务现场，并判断是否需要读取服务代码。

如果你想手动登记，也可以运行：

```powershell
codex-workbench service add user-api --path E:\AI\services\user-api --purpose "用户接口服务"
codex-workbench service update user-api --purpose "用户接口服务"
codex-workbench service context user-api
```

注意：

- `service add/update/delete` 只管理服务登记，不接管业务仓库。
- Workbench 不会 clone、切分支、提交或推送业务仓库。
- `service_refs` 是任务和服务的上下文索引，不是修改白名单。
- 能不能修改某个服务，仍然取决于任务阶段、风险边界、用户授权和真实代码现场。

## 4. 开始第一个需求

使用 Workbench 时，最推荐的方式是用自然语言把目标告诉 Codex。

例如：

```text
我有一个新需求：用户后台需要支持导出操作日志。请先纳入 Workbench，不要急着写代码，先整理材料、待确认点和可能涉及的服务。
```

Codex 通常会先做这些事：

1. 判断这是不是普通讨论、只读探索、小修，还是正式产品需求。
2. 如果需要长期跟踪，会登记材料、整理发现，并形成一份等你确认的需求草案。
3. 等你确认需求边界后，再创建正式需求和任务。
4. 如果涉及服务，会把服务挂到任务上。
5. 开工前检查目标、范围、风险和验证方式是否足够清楚。
6. 实现后记录验证事实、验证判断和用户交接状态。

你可以这样控制节奏：

- “先讨论，不要写状态。”
- “这个要纳入 Workbench。”
- “这个先只读探索，不要改代码。”
- “这个可以作为小修处理。”
- “这个任务可以开始做了吗？先帮我检查一下条件够不够。”
- “我已验收，通过后再考虑关闭需求。”

## 5. 日常使用场景

### 聊天或方案讨论

直接说你的问题即可：

```text
你觉得这个方案有没有风险？先讨论，不需要写状态。
```

Workbench 不会因为聊天自动创建任务。

### 只读探索

适合先了解现状：

```text
先了解 user-api 的认证模块，不要改代码，给我说清楚风险和入口。
```

Codex 可以读取必要文件和只读命令，但不默认写状态。

### 小修

适合边界清楚、影响小、可验证、可回滚的修改：

```text
这个展示文案有错，影响很小，直接帮我修一下并跑相关验证。
```

如果调查中发现影响变大，Codex 应该暂停并说明风险。

### 正式任务

适合需要长期跟踪、阶段推进、验证证据和用户验收的工作：

```text
这个需求要正式纳入 Workbench。请先整理材料和待确认问题，不要直接写代码。
```

正式任务的重点不是仪式，而是避免“未确认需求、未验证代码、未交接状态”被误当成完成。

### 验证和完成

当你认为任务已经完成时，可以说：

```text
我验收通过了，帮我收尾，看看现在能不能标记完成。
```

Codex 会按 Workbench 规则自动检查完成条件；如果缺少验证记录、验证判断或交接信息，它应该先告诉你缺什么，而不是直接标记完成。

Workbench 在后台会把这些事情拆开处理：

- 验证事实：真实执行过什么检查、测试或人工确认。
- 验证判断：这些事实是否足以说明任务完成。
- 用户交接：你是否验收、还有没有后续注意事项。

三者不能互相替代。

### 关闭和归档

任务 done 不等于需求关闭，需求关闭也不等于归档授权。

你可以分开说：

```text
这个需求可以关闭。
```

```text
我授权把这个需求归档成一个版本。
```

Workbench 会把关闭和归档分成两个动作，避免误操作历史。

## 6. 可复用经验

Workbench 可以维护一组给白天 Codex 使用的可复用经验：

```text
docs/reusable/
  workflow.md
  services.md
  validation.md
  architecture.md
  environment.md
  patterns.md
  pitfalls.md
```

日常你可以让 Codex 自己查：

```text
这个任务可能和以前的验证规则有关，先查一下 reusable memory。
```

可复用经验只是思路入口，不是真源。遇到高风险、环境、部署、数据、权限或当前事实冲突时，仍然要回到真实代码、环境资料、policy 和命令输出核验。

## 7. Workbench 保存了什么

| 内容 | 位置 |
| --- | --- |
| 当前需求和任务 | `docs/active/` |
| 当前面板和恢复视图 | `CURRENT.md`、`docs/generated/` |
| 服务登记 | `services/registry.yaml` |
| 环境资料 | `environments/` |
| 归档历史 | `docs/archive/` |
| 规则说明 | `docs/policies/` |
| Codex 场景手册 | `.agents/skills/workbench-*` |
| Codex 轻提醒 | `.codex/hooks.json`、`.codex/hooks/` |
| 可复用经验 | `docs/reusable/` |
| CLI 实现 | `src/codex_workbench/` |

真正的状态以 YAML 和真实文件为准；`CURRENT.md` 和 `docs/generated/` 是可重建视图，只用于定位和恢复。

事实证据层级：

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

## 8. 常用命令参考

普通使用者可以跳过本节。Codex 会在需要时调用这些命令，并用 `--help` 核对参数。

```powershell
codex-workbench workspace context --workspace-root .
codex-workbench service add <服务名> --path <本地服务路径> --purpose "<服务用途>"
codex-workbench service update <服务名> --purpose "<新用途>"
codex-workbench service delete <服务名>
codex-workbench service context <服务名>
codex-workbench task context <任务名或ID>
codex-workbench task check <任务名或ID> --to in_progress
codex-workbench task check <任务名或ID> --to done
codex-workbench reusable-memory find <关键词>
codex-workbench index check --workspace-root .
codex-workbench doctor check --workspace-root .
```

完整命令不用背，进入对应场景后让 Codex 查 `--help` 即可。

## 9. 排错

### `ModuleNotFoundError: No module named 'typer'`

说明当前 Python 没装项目依赖。回到仓库根目录安装：

```powershell
python -m pip install --user -e ".[dev]"
```

如果安装后仍找不到 `codex-workbench` 命令，确认 Python 用户脚本目录已加入 PATH，然后重启 Codex Desktop 或新开终端。

```powershell
$env:APPDATA\Python\Python313\Scripts
```

### 找不到 Workbench 根目录

确认你当前在仓库根目录，或者命令带上：

```powershell
--workspace-root <你的 Workbench 目录>
```

### `CURRENT.md` 看起来不对

`CURRENT.md` 是生成视图，不是真源。先检查：

```powershell
codex-workbench index check --workspace-root .
```

如果需要重建，再让 Codex 核对 `index generate --help` 后执行。

### 没有 active task

这不一定是错误。可能当前只是讨论、只读探索、仓库维护，或者需求还没有被你确认为 readable requirement。

## 10. 红线

- 没有用户确认的 readable requirement，不创建正式产品 task。
- 正式产品 task 未进入 `in_progress` 或 implementation-ready 不清时，不修改任务目标内文件。
- `service_refs` 是相关服务标记，不是修改白名单。
- 涉及环境、账号、数据、部署、安全、权限、费用、不可逆操作、影响他人或共享环境时，先确认授权和风险边界。
- 没有 evidence，不声称已验证或已完成。
- action note、doctor clean、测试计划、gate-check、口头判断都不能替代 task evidence。
- 用户验收、task done、requirement close、archive authorization 不能互相替代。

## 11. 进一步阅读

- `AGENTS.md`：Codex 进入本仓库时的热路径入口。
- `.agents/skills/workbench-*`：恢复、任务、门禁、环境、验证、归档等场景手册。
- `docs/policies/`：流程、风险、状态、材料、服务环境和模型语义的冷路径规则。
- `.codex/automations/reusable-materials/runbook.md`：夜间可复用记忆维护手册。
- `src/codex_workbench/`：CLI、模型和 schema 实现；只有想看实现时才需要读。

## 12. 禁用或绕开

- 禁用 hook：移走或删除 `.codex/hooks.json`。
- 禁用 skills：移走或删除 `.agents/skills/workbench-*`。
- 不想进入正式任务：保持在讨论、只读探索或小修模式，不创建 requirement/task。

Workbench 应该帮助 Codex 稳定工作，而不是把每次对话都变成流程。它真正想保住的是：事实、边界、证据、恢复能力和长期可复用经验。
