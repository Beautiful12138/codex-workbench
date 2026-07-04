# Reusable Materials Nightly Guide

本文件是夜间 Codex 的工作指导手册。每次自动化启动后先读本文件，再读 `handoff.md`。

本文件只给夜间 Codex 使用。白天 Codex 只读取 `docs/reusable/*.md`，不需要知道夜间自动化、SQLite、handoff、容量规则或维护流程。

## Mission

每天从已完成、已确认、已归档或已验证的工作中，沉淀少量未来可复用的记忆，并保持 `docs/reusable/` 简洁、可信、不过度膨胀。

夜间 Codex 只允许维护：

- `docs/reusable/*.md`
- `.codex/automations/reusable-materials/handoff.md`
- `.codex/automations/reusable-materials/ledger/YYYY-MM.sqlite`

不要修改业务代码、任务包、policy、skill、AGENTS、环境资料或 generated views，除非用户明确把夜间自动化本身作为维护任务交给你。

## Operating Principles

- 开发优先：候选范围保持偏开放，优先寻找能帮助白天 Codex 开发、排错、验证、读环境和判断边界的材料。
- 信息够用：不要为了压缩而删掉未来开发会用到的关键路径、命令、边界条件、取舍理由和验证入口。
- 当前有效：只保留仍被当前代码、policy、schema、环境边界支持的记忆。
- 可复用：记忆必须能指导未来多个任务，而不是解释某一次需求历史。
- 白天友好：白天 Codex 读到的是干净知识，不是维护日志。
- 可回源：夜间 Codex 自己要能在 ledger 里追溯为什么改，但不要把来源写进白天文件。
- 不信任旧记忆：旧记忆被当前事实反证时，优先更新或删除。
- 不确定就暂缓：证据不足、维度不清或复用价值不清时，不沉淀；涉及环境、账号或部署概念不自动跳过，只过滤真正可直接滥用的秘密值。

## Start Checklist

1. 读取本 guide。
2. 读取 `.codex/automations/reusable-materials/handoff.md`。
3. 确认当前工作区是 `codex-workbench` 根目录。
4. 初始化当月 ledger。
5. 新增或恢复一条 `nightly_run`，确保本次维护有明确 `run_id`，初始或恢复状态为 `result=partial`。
6. 计算并暂存每个维度运行前的条数 `before_count`；不要在开始阶段写入 `dimension_count`，等该维度处理完成后一次性记录 before/after。
7. 开始只读查找候选材料。

如果第 3-5 步失败，不要修改 `docs/reusable/`；尽量在可用位置记录失败原因，或在最终响应中说明失败。

## Candidate Sources

优先从这些地方找候选：

- 昨天以来进入 `done`、`obsolete`、`verification_pending` 或有新 evidence / handoff 的 active task。`verification_pending` 可提炼已实现路径、验证入口和风险边界；`obsolete` 可提炼废弃原因、误判模式和不再采用的边界，不沉淀已废弃方案本身。
- 最近归档的 requirement / task。
- 用户明确确认过的需求边界、验收口径、风险接受或长期决策。
- task 绑定的 service、源码、测试、配置、CLI 入口和环境资料。候选范围偏开发，不要只读文档摘要；必要时读取真实代码和环境说明来判断知识是否可复用。
- `handoff.md` 中上一晚留下的 watch / carryover。

可读位置：

- `docs/active/`
- `docs/archive/`
- `docs/generated/index.md`
- `docs/generated/recovery.md`
- `docs/actions/`
- `docs/changes/`
- `docs/decisions/`
- `docs/suspicions/`
- `services/registry.yaml`
- task / requirement 绑定的服务目录
- `environments/`
- `docs/reusable/*.md`

读取原则：

- 先看 generated views 或 registry 定位，再读具体 YAML / Markdown / 代码。
- 只读代码、测试、配置和环境资料；不要改它们。
- 不运行有外部影响的服务命令。
- 不读取 archive 全量历史；只读与候选相关的版本。
- 不设很小的候选上限；如果候选确实围绕开发经验、代码入口、验证路径或环境边界，可以继续深读。
- 不做无目标全仓扫描；深读应能说清它服务哪个候选、维度或旧记忆校准。

## Candidate Questions

每个候选都先问：

1. 未来白天 Codex 真会复用它吗？
2. 它能跨需求、跨任务或跨服务复用吗？
3. 它是否能用清晰结构说清，且保留足够未来开发可用的上下文？
4. 它是否已经被当前代码、policy、schema 或用户新结论支持？
5. 它是否能替代、更新或合并已有记忆？
6. 它是否只是一次性现场、临时路径、旧日志或局部实现细节？
7. 它是否包含可直接滥用的秘密值？
8. 它会让白天 Codex 读更少，还是读更多？

只有前 5 个答案明确为“是”，且后 3 个答案明确为“否/不会”，才考虑沉淀。不要因为内容需要多写几段就跳过；只要它能减少未来白天 Codex 的摸索成本，就允许更丰满的记忆片段。

## Action Decision

对每个候选选择一个动作：

- `add`：已有记忆没有覆盖，候选有明确复用价值。
- `update`：已有记忆方向正确，但内容过期、不完整或需要改写。
- `delete`：已有记忆被事实反证、过期、太具体、无法核验或没有复用价值。
- `merge`：多条记忆讲同一主题，应压成一条更短的高价值记忆。
- `reorder`：只调整编号或排序，不改变内容。
- `skip`：候选不够确定、不够复用、含秘密值、太具体或当前维度容量不适合新增。

默认选择 `skip`。不要为了让夜间运行看起来有产出而新增记忆。

如果新记忆要完全替代旧记忆，ledger 中按 `update` 记录；如果需要先删旧主题再新增另一个主题，按 `delete` + `add` 分别记录。不要使用脚本不存在的 `replace` 动作。

## Dimension Guide

`workflow.md`：
流程、阶段、门禁、协作方式、什么时候该停下、什么时候该补 evidence。

`services.md`：
服务登记、服务上下文、服务间关系、常见入口、服务级验证路径。可以写非秘密的服务名、目录、命令入口、验证入口和环境别名；不要写密码、token、私钥、cookie 或完整连接串。

`validation.md`：
测试、验证、evidence、handoff、验收、done 判断。不要写一次性测试输出长日志。

`architecture.md`：
稳定架构关系、模块边界、跨服务契约、重要设计取舍。不要写尚未确认的推断。

`environment.md`：
环境资料怎么查、使用前要确认什么、哪些动作有风险。可以写环境名称、系统角色、查询入口、操作前置条件和脱敏示例；不要写可直接登录或调用的秘密值。

`patterns.md`：
重复出现的实现模式、代码组织方式、CLI 使用模式、文档维护模式。

`pitfalls.md`：
反复踩到的坑、误判、容易混淆的概念、错误完成方式。

如果一个候选可以进入多个维度，选择白天 Codex 最可能查找的那个维度；不要复制到多个文件。

## Memory File Format

白天可见文件固定为：

- `docs/reusable/workflow.md`
- `docs/reusable/services.md`
- `docs/reusable/validation.md`
- `docs/reusable/architecture.md`
- `docs/reusable/environment.md`
- `docs/reusable/patterns.md`
- `docs/reusable/pitfalls.md`

每个文件只使用：

```md
# Dimension

## 1. 标题
内容
```

规则：

- 一个 `## 编号. 标题` 是一条记忆。
- 标题要短，直接说明可复用知识。
- 正文允许更丰满：可以写 2-8 个短段落、短列表、关键命令、路径、判断条件和验证入口。
- 保留未来开发会用到的上下文，但不要复制整段源码、长日志或完整环境资料。
- 编号必须连续。
- 不写来源、标签、更新时间、容量规则、维护说明、tombstone、候选、审计字段或夜间交接。
- 不把大段源码、日志、环境正文复制进记忆；需要引用时只写相对路径、入口名称或脱敏片段。

## Capacity Rules

每个维度独立计算：

- 20 条以下：除非发现错误或过期，否则不需要为了数量专门维护。
- 达到 30 条：新增前必须主动考虑压缩、合并或删除低价值记忆。
- 达到 50 条：硬上限；必须舍弃、合并或替换旧记忆后才能新增。

容量处理顺序：

1. 删除被事实反证或无复用价值的记忆。
2. 合并同主题或相邻主题记忆。
3. 改写过长或重复记忆，但不要牺牲未来开发真正需要的细节。
4. 用更高价值的新记忆替换低价值旧记忆。
5. 仍无法腾出空间时，跳过候选。

不要创建第 51 条。

## Write Protocol

每个维度按这个顺序处理：

1. 读取维度文件当前内容。
2. 解析当前记忆列表和条数，暂存 `before_count`。
3. 选择候选动作：add / update / delete / merge / reorder / skip。
4. 写入前先推演 `after_count`；如果会超过 50 条，必须先删、合并或改为跳过。
5. 对每条实际变更暂存单条记忆的 `content_before` / `content_after`，只存这条记忆，不存整个维度文件。
6. 写出修改后的维度文件，保持格式和编号连续。
7. 重新读取文件，检查格式、编号、容量、秘密值和夜间噪音。
8. 用 ledger 记录每条实际变更的 before / after。
9. 对检查过的维度写入一条 `dimension_count`，同时包含 `before_count` 和 `after_count`。

`skip` 不需要写 `memory_change`；如果值得下一晚接着看，写入 `handoff.md` 的 `Watch Next`。

如果已经修改了 `docs/reusable/`，但 ledger 记录失败：

- 不要继续扩大修改。
- 尝试修复 ledger 写入。
- 修复失败时，在 `handoff.md` 写清楚本次未完成的记录事项。
- `nightly_run.result` 标记为 `partial` 或 `failed`。

如果 ledger 可用但维度文件写入失败：

- 不要伪造变更记录。
- 记录失败原因到 `nightly_run.summary` 或 `handoff.md`。

## Ledger Protocol

Ledger 是夜间流水账，不是白天知识入口，不是状态真源。

每月一个 SQLite：

```text
.codex/automations/reusable-materials/ledger/YYYY-MM.sqlite
```

启动方式：

```powershell
python .\.codex\automations\reusable-materials\reusable_ledger.py --help
```

如果 `--help` 失败，停止本次维护，不要修改 `docs/reusable/`。失败原因写入最终响应；如果 handoff 仍可安全写入，可以只写恢复提示。

常用命令：

以下 `python` 表示用户环境里已安装 Workbench 依赖的 Python，并且已经通过上面的 `--help` 检查。

```text
python .codex/automations/reusable-materials/reusable_ledger.py init
python .codex/automations/reusable-materials/reusable_ledger.py add-run
python .codex/automations/reusable-materials/reusable_ledger.py update-run
python .codex/automations/reusable-materials/reusable_ledger.py add-dimension-count
python .codex/automations/reusable-materials/reusable_ledger.py add-change
python .codex/automations/reusable-materials/reusable_ledger.py list-runs
python .codex/automations/reusable-materials/reusable_ledger.py list-changes
python .codex/automations/reusable-materials/reusable_ledger.py show-change
```

正常流程：

1. `init` 初始化当月 ledger。
2. `list-runs` 查看今天是否已有明显属于本次中断恢复的 `partial` run；如果有，复用该 `run_id`，否则执行 `add-run --result partial`。
3. 捕获 `add-run` 标准输出里的数字作为 `run_id`，后续所有 `add-change`、`add-dimension-count`、`update-run` 都必须带这个 `run_id`。
4. 开始处理维度前，把各维度 `before_count` 暂存在当前会话里，不写 SQLite。
5. 每条实际变更完成并复核后，执行 `add-change`。
6. 每个维度处理完成后，执行一次 `add-dimension-count --count-before ... --count-after ...`。
7. 结束前用 `list-changes --run-id <run_id>` 复查本次变更，再用 `update-run` 写入 `result`、summary 和 add/update/delete/merge 计数。
8. 最后用 `list-runs` 确认本次 run 已从 `partial` 更新为 `completed`、`partial` 或 `failed`。

中断恢复：

- 如果 `docs/reusable/` 已被修改但本次 `memory_change` 缺失，先补 ledger，不要继续扩大修改。
- 如果无法可靠还原某条变更的 before/after，`nightly_run.result` 保持 `partial` 或 `failed`，并在 `handoff.md` 写清需要人工或下一晚处理的缺口。
- 如果只是 `update-run` 未完成，先用 `list-changes --run-id <run_id>` 汇总，再补 `update-run`。

记录要求：

- 每晚必须有一条 `nightly_run`。
- 每个检查过的维度都记录一条 `dimension_count`，同时包含维护前和维护后的数量。
- 每条实际 add / update / delete / merge / reorder 都记录 `memory_change`。
- `content_before` 和 `content_after` 只存单条沉淀记忆全文，不存整个维度文件。
- `audit_sources` 只写来源路径或任务线索，不写来源正文。
- 长文本优先使用 `--content-before-file` / `--content-after-file`，避免 PowerShell 转义问题。

SQLite 的任何字段都不要写入密码、token、私钥、cookie、完整连接串或可直接滥用的原始秘密值。可以写非秘密的路径、任务线索、服务名、环境别名、表名、队列名和脱敏判断依据。

## Handoff Protocol

`handoff.md` 是夜间到夜间的交接，不给白天 Codex 使用。

每晚重写，不追加。

必须保留：

- `last_run`
- `result`
- `run_id`
- `ledger`
- `Carryover`
- `Watch Next`
- `Last Run Summary`

`Last Run Summary` 使用固定口径：added / updated / deleted / merged / reordered / skipped，以及一句本晚最重要的判断。`reordered` 和 `skipped` 只写在 handoff 摘要里，`update-run` 的数量字段仍按脚本支持的 add/update/delete/merge 填。

只写下一晚需要接续的事情：

- 未完成的 ledger 记录。
- 达到 30 或 50 条的维度提醒。
- 需要复查的旧记忆。
- 本晚跳过但值得下次再看的候选。
- 失败原因和恢复方式。

不要写：

- 完整历史。
- 完整 evidence。
- 来源正文。
- 原始秘密值。
- 白天 Codex 使用说明。

`handoff.md` 不超过 100 行。

## Sensitive Information Rules

边界保持开放：不要因为候选涉及环境、账号概念、部署、数据库、队列或外部系统就自动跳过。夜间 Codex 要沉淀可复用的开发线索，但过滤真正可直接滥用的秘密值。

禁止写入 `docs/reusable/`、SQLite 任意字段和 handoff 正文：

- 密码
- token
- secret
- api key
- cookie
- Authorization
- Bearer token
- 私钥
- 完整数据库连接串
- 账号 + 凭证的可直接登录组合
- 含秘密值的日志原文
- 大段源码或完整环境正文

可以写：

- 环境名称、系统名、服务名、目录、相对路径和 CLI 入口。
- 数据库、表、队列、Nacos namespace、配置项名称等非秘密标识。
- 账号角色或用途，例如“只读账号”“后台管理员角色”，不写凭证值。
- 地址、域名或连接信息的别名 / 脱敏形式；如果真实地址本身对开发判断必要且已存在于项目环境资料中，只写最小必要片段，不和凭证组合成可直接访问材料。
- 使用前需要什么授权、有什么风险边界、哪些操作必须再次确认。

如果候选只有暴露秘密值才有用，不写秘密值；改写成“去哪里查、如何确认授权、使用前要注意什么”。

## Failure Handling

没有候选：

- 不修改 `docs/reusable/`。
- 记录 `nightly_run.result=completed`，summary 写明 no candidate。
- 重写 handoff，保留必要 watch。

候选不确定：

- 选择 `skip`。
- 如值得下次看，写入 handoff 的 `Watch Next`。

容量达到 50：

- 不新增。
- 优先删除、合并或替换。
- 做不到时跳过，并在 handoff 里标记该维度。

发现秘密值或高敏片段：

- 不复制秘密值。
- 可沉淀脱敏后的开发线索、查询入口、授权前置条件和风险边界。
- 如有风险，handoff 只写脱敏提醒。

发现旧记忆错误：

- 优先 update 或 delete。
- 如果无法确认正确替代内容，delete 或写入 handoff 待复查，不保留明显错误的记忆。

## Finish Checklist

结束前检查：

- `docs/reusable/*.md` 只包含 `# Dimension` 和 `## 编号. 标题` 记忆。
- 每个修改过的维度编号连续。
- 每个维度未超过 50 条。
- 达到 30 条的维度已考虑压缩、合并或删除。
- 没有来源字段、标签、更新时间、容量规则、tombstone、候选、夜间说明。
- 没有原始秘密值、源码正文或日志原文。
- 每条实际变更都有 ledger 记录。
- 每个检查过的维度都有 count 记录。
- `nightly_run` 已更新为 `completed`、`partial` 或 `failed`。
- `handoff.md` 已重写，且只保留下一晚需要的信息。

如果不能满足以上检查，不要把本次运行标记为 `completed`。
