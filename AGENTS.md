# Codex Workbench 入口地图

本文件是 Codex 进入 Workbench 时的入口地图，不是完整手册。启动时先读这里，再按当前动作读取 `CURRENT.md`、生成视图、任务包或 policy。

普通讨论不写状态、低风险任务少仪式；当请求进入任务推进、验证、交接或归档时，按本文件、policy、skills 和 CLI 规则恢复现场、判断边界并留下证据。

## 工作区定位

当前仓库既是 Workbench baseline 工作空间，也是 `codex_workbench` Python 包仓库。

`workspace_status: baseline` 表示这里还没有绑定真实需求；它是后续真实需求、任务包和服务登记的干净起点。

## 读取顺序

恢复现场、回答状态问题或准备推进任务时，按顺序读取：

1. `AGENTS.md`
2. `CURRENT.md`
3. `docs/generated/recovery.md` 或用户明确给出的包路径
4. 当前 requirement / task 包中的 YAML 和 Markdown
5. 只有动作需要时，读取 `docs/policies/*`、`services/registry.yaml` 或 `docs/archive/*`

普通讨论不需要展开全部状态；只读探索不等于修改授权。

## 动作模式与读取深度

| 当前动作 | 默认读取 | 何时展开更多 |
| --- | --- | --- |
| 普通讨论 / 方向判断 | `AGENTS.md`、`CURRENT.md` | 需要固化结论时再读包和 policy |
| 只读探索 | 用户指定文件、生成视图、相关服务状态 | 需要落 discovery / intake 时再写材料或发现 |
| 产品任务推进 | 当前 requirement / task 包、`services/registry.yaml` | 修改前确认任务已 `in_progress` 且范围清楚 |
| 验证 / 交接 / 完成 | task 包、evidence、handoff | 标记 done 前必须读取真实 evidence |
| 版本归档 | 已关闭 requirement、done/obsolete task、archive policy | 必须有需求关闭确认和独立归档授权 |

## 动作分流

不是所有请求都进入正式任务。

- 普通讨论、头脑风暴、解释和只读探索默认不写状态。
- 产品需求先进入 material / discovery / intake；用户确认 readable 后才能创建正式 task。
- 维护动作可写 action note，但 action note 不替代 task evidence。
- action note 只记录 `maintenance_action`、`ops_action` 或 `ephemeral_check`；产品任务仍进入 task。
- 需求目标、验收、范围或真实后果变化时，走 change record。

## 状态真源

- `CURRENT.md`：入口卡和当前恢复提示。
- `docs/active/*/*.yaml`：requirement、task、evidence 等机器状态真源。
- `docs/active/*/*.md`：给人和 Codex 的解释，不覆盖 YAML。
- `services/registry.yaml`：服务登记和只读状态输入；`service_refs` 只是相关服务标记，修改授权来自用户请求、任务阶段、working_scope 和风险边界；写出的 service ref 必须能对应已登记服务。
- `docs/generated/`：可重建视图，不覆盖包真源。
- `docs/archive/`：版本化冷历史，默认不作为当前上下文。

## 事实层级

从高到低：人工确认和命令输出、evidence、action note、progress、requirement、discovery、generated view、current packet、AI 推断、未确认假设。低层级不能覆盖高层级。

## 最高优先级边界

- 没有用户确认的 readable requirement，不创建正式 task。
- 没有 `in_progress` task 和清楚范围，不修改任务目标内文件。
- 没有 evidence，不声称已验证或已完成。
- 不让自动提醒或健康检查替代人工判断、自动写状态、自动归档、自动修复或阻断普通探索。
- 真实数据、部署、安全、权限、费用、不可逆操作或影响他人时，暂停确认；触发任务 `risk_triggers` 时也先暂停。

## Policy 地图

- `docs/policies/action-routing.md`：动作分流和非任务记录。
- `docs/policies/state-and-gates.md`：阶段、门禁、evidence、handoff、done 和 archive。
- `docs/policies/materials.md`：材料、discovery、intake 和事实边界。
- `docs/policies/services-and-environment.md`：服务登记、`service_refs` 语义和外部环境边界。
- `docs/policies/agent-coordination.md`：Codex skills、子代理复核和高风险协作。
- `docs/policies/lifecycle-semantics.md`：生命周期细节。
- `docs/policies/model-schema.md`：核心模型和 schema 细节。

## 本地 Skills

本仓库的 Workbench skills 位于 `.agents/skills/`。

当任务涉及恢复现场、任务推进、验证交接或版本归档时，优先查看并按需使用这里的 skills。不要默认到其他仓库或全局目录寻找同名 Workbench skills。

skills 应提供真实操作规程，不只是短提醒；但状态真源仍是 `CURRENT.md`、包 YAML、evidence 和用户确认。

## 自动提醒与健康检查

启动提醒和健康检查都是辅助信号，不是状态真源。

不要根据提醒或健康检查自动推进阶段、归档、修复文件或替代 evidence；需要维护细节时再查看 README、WORKSPACE 或对应 policy。
