# codex-workbench

`codex-workbench` 是一个个人本地 Codex 工作空间底座。它把基线工作空间、Python CLI、schema、doctor、生成视图、归档、Codex hooks 和本地 skills 放在同一个仓库里，让一个人可以在多个项目/服务之间轻量协作、恢复上下文、保留证据，并尽量少越界。

V1 不做 Web UI，不深度接管外部服务仓库的 clone、branch、commit、worktree 或 push；服务仓库只做登记、关联和只读状态检查。

## 进入工作空间

新窗口或新 AI 进入时先读：

1. `AGENTS.md`：入口地图，说明读取顺序、动作分流、状态真源和边界。
2. `CURRENT.md`：当前入口卡，说明 baseline 或当前工作对象。
3. `docs/generated/recovery.md` 或用户明确给出的包路径。
4. 当前 requirement / task 包。

普通讨论、解释和只读探索默认不写状态。只有用户明确要纳入、创建、推进、验证、关闭或归档时，才进入 CLI 和包写入。

## 主路径

从想法到完成通常是：

1. `material add`：登记材料来源和脱敏摘要。
2. `discovery create`：记录只读探索得到的观察、AI 推断、假设和待确认问题。
3. `intake create` / `intake confirm`：形成 AI-readable 需求；用户确认后才能创建正式任务。
4. `task create`：创建任务包，任务包是执行界面。
5. `evidence create`：记录真实验证事实。
6. `validation apply`：把 evidence 判断写回任务。
7. `handoff set`：记录用户验收交接状态。
8. `task set-stage --stage done`：在 evidence、validation、handoff 都满足时完成任务。
9. `requirement close` + `archive preflight/version`：用户确认需求关闭并授权归档后，版本化归档。

生成视图只用于恢复和检索，不覆盖包 YAML 真源。

## CLI 能力

- `material add/list`：登记材料脱敏摘要。原件默认不复制、不提交。
- `discovery create`：记录系统观察、AI 推断、假设和待确认问题。
- `intake create/confirm`：把材料和发现转成 intake 草案；确认后才成为 readable requirement。
- `requirement close`：追加需求关闭确认；它不替代归档授权。
- `task create` / `task review-create` / `task implementation-create` / `task prepare` / `task check` / `task block` / `task obsolete` / `task set-stage`：创建任务、在任务包本地生成 review/implementation Markdown、写入 implementation-ready 和可选 `risk_triggers` 暂停条件，只读预演阶段门禁，记录阻塞或废弃说明，并受 lifecycle guard 推进阶段。
- `evidence create` / `validation apply` / `handoff set`：记录验证事实、验证结论和用户交接。
- `service add/list/status`：登记服务并做只读状态检查；`service_refs` 是相关服务标记，不是修改白名单，但写出的 service ref 必须能对应已登记服务。
- `action create` / `change classify/create` / `decision create` / `suspicion create`：记录非任务动作、范围澄清或变化、长期决策和疑点线索；action note 只接受 `maintenance_action`、`ops_action`、`ephemeral_check`，可选记录状态、授权、目标和结果。
- `index generate/check`：从 YAML 真源生成 `docs/generated/index.md` 和 `docs/generated/recovery.md`。
- `doctor check`：只读健康检查，默认极简，只展开 Blocking。
- `archive preflight/version/list`：按版本归档已关闭 requirement 及其任务包。

## 工作产物模板

`templates/work-products/*.md` 是 requirement、task、evidence、review、implementation、action、change、decision 和 suspicion 的 Markdown 起稿骨架，只用于稍微统一格式。CLI 只渲染身份标题和章节骨架，不把 YAML 参数灌进 Markdown 正文；标题、章节和表达方式都可以由 AI 按当前任务自由删改。

所有结构化字段保存在对应 YAML 中，Markdown 默认保留少量章节标题，给 AI 一个统一起稿标准；正文按真实场景自由组织。

`AGENTS.md`、`CURRENT.md`、policy、README 和 WORKSPACE 属于基线/工程文档，不在这套工作产物模板里。

## Codex 集成

- `.codex/hooks.json` 启用 `SessionStart` 和 `UserPromptSubmit` 两个轻量 hook。
- hook 只输出 1-3 行中文提醒，不写状态、不运行 doctor、不自动推进阶段、不自动归档。
- `.agents/skills/workbench-*` 提供按需技能：恢复现场、任务路由、验证交接、版本归档。
- skill 正文保持短；状态修改仍通过 CLI 和包 YAML 完成。

## Policy 地图

`docs/policies/` 是温路径。常用文件：

- `action-routing.md`：普通讨论、只读探索、产品任务、维护动作和归档动作怎么分流。
- `state-and-gates.md`：需求 readable、任务 in_progress、evidence、handoff、done 和 archive 的门禁。
- `materials.md`：材料、discovery、intake 和事实层级。
- `services-and-environment.md`：服务登记、`service_refs` 语义和外部环境边界。
- `agent-coordination.md`：skills、子代理复核和接续方式。
- `lifecycle-semantics.md` / `model-schema.md`：生命周期和模型 schema 的冷路径细节。

## 冒烟验证

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench version
python -m codex_workbench doctor check --workspace-root .
python -m pytest
```

## 禁用和回滚

- 禁用 hook：移走或删除 `.codex/hooks.json`。
- 禁用 skills：移走或删除 `.agents/skills/workbench-*`。
- 回滚 Workbench 集成：回退 `.codex/`、`.agents/skills/`、相关 CLI 薄适配、测试和文档。
