# codex-workbench

`codex-workbench` 是个人本地多项目工程协作工作台。它帮助 Codex 在多个需求、多个任务、多个服务之间稳定工作：恢复现场、判断请求类型、选择工作对象、留下验证证据、保留历史，并尽量少越界。

它由几部分组成：

- 运行期入口：`AGENTS.md`、`WORKSPACE.md`
- 动态当前面板：`CURRENT.md`
- 状态包：`docs/active/`、`docs/inbox/`、`docs/archive/`
- 生成视图：`docs/generated/index.md`、`docs/generated/recovery.md`
- 规则：`docs/policies/`
- 服务登记：`services/registry.yaml`
- 环境资料：`environments/*.md`
- 操作规程：`.agents/skills/workbench-*`
- CLI/schema：`src/codex_workbench/`
- 工作产物模板：`templates/work-products/`
- Codex 轻提醒：`.codex/hooks.json` 与 `.codex/hooks/`

## 进入工作台

新的 Codex 或新窗口进入时按顺序读取：

1. `AGENTS.md`：热路径入口地图。
2. `workspace context`：按需驾驶舱，不生成文件；默认只读 registry 做轻量服务概览。
3. 用户明确给出的路径、需求/任务名称、ID 或服务名。
4. 选中 task 后优先用 `task context <任务名或ID>`；涉及服务时优先用 `service context <服务名>`。
5. 需要细节时再读被选中的 requirement / task 包 YAML 和 Markdown。

默认路径：workspace context -> task context -> service context -> task package。需要服务路径/Git/入口探测时，再用 `service context <服务名>` 或 `workspace context --check-services`。`task context` 对批量 `service_refs` 默认只展开前 5 个唯一服务；若剩余服务未检查，代码修改能力会提示 `service_check_limited`，可用 `--service-check-limit` 显式扩大检查范围。`CURRENT.md`、`docs/generated/recovery.md` 和 `docs/generated/index.md` 仍可作为生成视图辅助定位，但不是真源。

涉及测试环境、服务器、数据库、GitLab、网站、联调、账号密码或操作方式时，再读取 `environments/` 下相关 Markdown。该目录是本地环境资料夹，不由 CLI 管理。

普通讨论、解释和只读探索默认不写状态。只有用户明确要纳入、创建、推进、验证、关闭、归档或留下可恢复记录时，才进入 CLI 和包写入。

创建 requirement、intake 草案或 task 时，可以省略 ID 和 `--updated-at`；CLI 会按当前日期生成 `REQ-YYYYMMDD-NNN` / `REQ-...-TASK-YYYYMMDD-NNN`，并写入当前时间。
创建成功后，CLI 会回显 `created requirement_id=...` 或 `created task_id=...`，后续命令应优先使用这个回显 ID。

## 正式产品任务闭环

小修、只读探索和普通讨论不默认走这条链；只有用户要纳入 Workbench、长期跟踪、推进阶段、验证或归档时使用。

从需求材料到归档通常是：

1. `material add`：登记材料来源和脱敏摘要。
2. `discovery create`：记录只读探索得到的观察、推断、假设和待确认问题。
3. `intake create`：形成 AI-readable 需求草案。
4. `intake confirm`：用户确认后 requirement 才 readable。
5. `task create`：创建任务包。
6. `task context`：查看当前任务工作面、服务现场、能力矩阵和缺口。
7. `task prepare`：写入开工范围、暂停条件、验证要求和 implementation-ready。
8. `task check --to in_progress`：只读预演门禁。
9. `task set-stage --stage in_progress`：通过门禁后进入实现。
10. `evidence create`：记录真实验证事实。
11. `validation apply`：把 evidence 判断写回 task。
12. `handoff set`：记录用户验收交接状态。
13. `task check --to done`：只读预演完成门禁。
14. `task set-stage --stage done`：在 evidence、validation、handoff 都满足时完成任务。
15. `requirement close`：用户确认需求关闭。
16. `archive preflight` / `archive version`：用户独立授权后版本归档。

## 多需求、多任务、多服务

- `docs/active/<REQ-ID>/` 是需求包。
- `docs/active/<TASK-ID>/` 是任务包。
- 多个 requirement 和 task 可以同时存在。
- `CURRENT.md` 不锁定唯一任务，只展示最近更新的活动任务。
- `docs/generated/index.md` 是完整活动目录，按 YAML 真源生成。
- `docs/generated/recovery.md` 帮助 Codex 选择续接对象和发现异常。
- `services/registry.yaml` 登记相关服务；`service_refs` 是上下文标记，不是路径白名单。
- `environments/` 保存测试环境、服务器、数据库、GitLab、网站和操作方式等自由 Markdown 资料，AI 按需自动发现。
- 外部服务仓库的 clone、branch、commit、worktree、push 不由 Workbench 接管。

## CLI 能力

- `workspace root/context`：查找工作区根目录，或输出不落盘的轻量驾驶舱。
- `material add/list`：登记材料。
- `discovery create`：登记发现。
- `intake create/confirm`：创建并确认可读需求；创建时可自动生成 requirement ID 和时间。
- `requirement close`：记录需求关闭确认。
- `task create`、`task context`、`task prepare`、`task check`、`task set-stage`、`task block`、`task obsolete`：管理任务包、轻量工作面板和阶段门禁；创建时可自动生成 task ID 和时间。
- `task review-create`、`task implementation-create`：按需在任务包内生成说明文档。
- `evidence create`、`validation apply`、`handoff set`：记录验证事实、验证结论和用户交接。
- `service add/list/context`：登记服务，并做可接任务上下文判断；`service status` 主要用于调试和脚本。
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
