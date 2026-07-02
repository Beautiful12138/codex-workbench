# codex-workbench

`codex-workbench` 是个人本地多项目工程协作工作台。它帮助 Codex 在多个需求、多个任务、多个服务之间稳定工作：恢复现场、判断请求类型、选择工作对象、留下验证证据、保留历史，并尽量少越界。

它由几部分组成：

- 运行期入口：`AGENTS.md`、`WORKSPACE.md`
- 动态当前面板：`CURRENT.md`
- 状态包：`docs/active/`、`docs/inbox/`、`docs/archive/`
- 生成视图：`docs/generated/index.md`、`docs/generated/recovery.md`
- 规则：`docs/policies/`
- 服务登记：`services/registry.yaml`
- 操作规程：`.agents/skills/workbench-*`
- CLI/schema：`src/codex_workbench/`
- 工作产物模板：`templates/work-products/`
- Codex 轻提醒：`.codex/hooks.json` 与 `.codex/hooks/`

## 进入工作台

新的 Codex 或新窗口进入时按顺序读取：

1. `AGENTS.md`：热路径入口地图。
2. `CURRENT.md`：CLI 生成的最近工作面板。
3. 用户明确给出的路径、需求 ID、任务 ID 或服务名。
4. `docs/generated/recovery.md`：续接和异常队列。
5. 被选中的 requirement / task 包 YAML 和 Markdown。

普通讨论、解释和只读探索默认不写状态。只有用户明确要纳入、创建、推进、验证、关闭、归档或留下可恢复记录时，才进入 CLI 和包写入。

## 典型闭环

从需求材料到归档通常是：

1. `material add`：登记材料来源和脱敏摘要。
2. `discovery create`：记录只读探索得到的观察、推断、假设和待确认问题。
3. `intake create`：形成 AI-readable 需求草案。
4. `intake confirm`：用户确认后 requirement 才 readable。
5. `task create`：创建任务包。
6. `task prepare`：写入开工范围、暂停条件、验证要求和 implementation-ready。
7. `task set-stage --stage in_progress`：通过门禁后进入实现。
8. `evidence create`：记录真实验证事实。
9. `validation apply`：把 evidence 判断写回 task。
10. `handoff set`：记录用户验收交接状态。
11. `task set-stage --stage done`：在 evidence、validation、handoff 都满足时完成任务。
12. `requirement close`：用户确认需求关闭。
13. `archive preflight` / `archive version`：用户独立授权后版本归档。

## 多需求、多任务、多服务

- `docs/active/<REQ-ID>/` 是需求包。
- `docs/active/<TASK-ID>/` 是任务包。
- 多个 requirement 和 task 可以同时存在。
- `CURRENT.md` 不锁定唯一任务，只展示最近更新的活动任务。
- `docs/generated/index.md` 是完整活动目录，按 YAML 真源生成。
- `docs/generated/recovery.md` 帮助 Codex 选择续接对象和发现异常。
- `services/registry.yaml` 登记相关服务；`service_refs` 是上下文标记，不是路径白名单。
- 外部服务仓库的 clone、branch、commit、worktree、push 不由 Workbench 接管。

## CLI 能力

- `material add/list`：登记材料。
- `discovery create`：登记发现。
- `intake create/confirm`：创建并确认可读需求。
- `requirement close`：记录需求关闭确认。
- `task create`、`task prepare`、`task check`、`task set-stage`、`task block`、`task obsolete`：管理任务包和阶段门禁。
- `task review-create`、`task implementation-create`：按需在任务包内生成说明文档。
- `evidence create`、`validation apply`、`handoff set`：记录验证事实、验证结论和用户交接。
- `service add/list/status`：登记服务并做只读状态检查。
- `action create`、`change classify/create`、`decision create`、`suspicion create`：记录非任务动作、正式范围变化、长期决策和疑点线索。
- `index generate/check`：生成或检查 `CURRENT.md`、`docs/generated/index.md` 和 `docs/generated/recovery.md`。
- `doctor check`：只读健康检查。
- `archive preflight/version/list`：版本归档和历史查询。

## 工作产物

YAML 是机器状态真源，Markdown 是运行期解释层。CLI 不把 YAML 参数大段灌入 Markdown 正文；Markdown 由 Codex 根据真实任务填写。

模板位于 `templates/work-products/`。模板只提供起稿结构，不要求空仪式，不预生成无内容的 review、implementation、evidence 或 change。

## 验证

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench version
python -m codex_workbench index check --workspace-root .
python -m codex_workbench doctor check --workspace-root .
python -m pytest
```

## 禁用

- 禁用 hook：移走或删除 `.codex/hooks.json`。
- 禁用 skills：移走或删除 `.agents/skills/workbench-*`。
