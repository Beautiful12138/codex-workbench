# 工作空间地图

这个目录是 `codex-workbench` 运行期工作台，也是 Workbench CLI 的源码仓库。它的核心职责是让 Codex 在多个需求、多个任务、多个服务之间稳定协作。

## 入口文件

- `AGENTS.md`：热路径入口地图，说明请求分流、读取深度、工作对象选择、状态真源、暂停条件和本地 skills。
- `CURRENT.md`：入口卡，只保存第一眼恢复提示，不作为单任务锁。
- `README.md`：人类使用说明和 CLI 主路径。
- `WORKSPACE.md`：本文件，说明目录职责。

## 运行期目录

- `docs/inbox/`：材料和 discovery 入口。
- `docs/active/`：并发工作单元；requirement、task、evidence 等活动包都在这里。
- `docs/generated/`：从 YAML 真源生成的 index 和 recovery 视图；可重建，不覆盖真源。
- `docs/archive/`：版本化冷历史；默认只在查询、恢复旧版本或归档时读取。
- `docs/policies/`：运行规则、阶段门禁、服务边界和协作规程。
- `docs/actions/`：非任务动作记录。
- `docs/changes/`：正式范围变化记录。
- `docs/decisions/`：长期决策记录。
- `docs/suspicions/`：疑点线索记录。
- `services/`：服务登记和只读状态输入。

## 工具目录

- `src/codex_workbench/`：Python CLI、schema、lifecycle guard、index、doctor、archive 和写入逻辑。
- `tests/`：模型、CLI、模板、doctor、archive、hooks 和端到端 dogfood 测试。
- `.agents/skills/`：Workbench 本地操作规程。
- `.codex/`：Codex 轻提醒 hook。
- `templates/work-products/`：运行期工作产物起稿模板。

## 工作流关系

1. 普通讨论和只读探索默认不写状态。
2. 产品需求先进入 material / discovery / intake。
3. 用户确认后，requirement 才 readable。
4. task 是执行界面，进入实现前必须准备范围、风险触发器、验证方式和恢复提示。
5. 多个 requirement 和 task 可同时存在，工作对象由用户请求、显式路径、ID 或 generated recovery 选择。
6. 服务登记帮助恢复上下文，不接管外部服务仓库 Git 生命周期。
7. 验证事实写入 evidence，validation 和 handoff 基于 evidence 与用户验收推进。
8. done、requirement close 和 archive 是独立门禁，不能互相替代。
