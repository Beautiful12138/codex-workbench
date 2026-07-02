# CURRENT

role: 入口卡
workspace: codex-workbench 基线
workspace_status: baseline
service_registry: services/registry.yaml
generated_views: docs/generated/
active_packages: docs/active/
updated_at: 2026-06-30

## 从这里开始

这个仓库是个人本地多项目工程协作工作台的基线工作区，同时包含 `codex_workbench` CLI 源码。

`CURRENT.md` 只提供第一眼恢复提示，不作为单任务锁，也不覆盖 `docs/active/*/*.yaml`。实际工作对象应从用户请求、显式路径、任务/需求 ID、`docs/generated/recovery.md` 或 CLI 参数中选择。

## 基线状态

- 尚未登记真实需求。
- 尚未登记真实任务。
- 尚未登记真实服务路径。
- `docs/generated/recovery.md` 当前应显示无 active tasks。
- `docs/policies/` 是运行规则地图，只在对应动作触发时读取。
- `docs/archive/` 是冷历史区域，只在查询、恢复旧版本或版本归档时读取。

## 下一步判断

- 普通讨论或只读探索：不写状态，按用户问题读取最少文件。
- 登记真实需求：先走 material / discovery / intake，用户确认 readable 后再创建 task。
- 推进已有任务：先从显式路径、任务 ID 或 generated recovery 选择任务包，再读取 task YAML/Markdown。
- 多任务并存：不要依赖本文件锁定焦点，按 `docs/policies/recovery-and-concurrency.md` 选择工作对象。
- 开发 Workbench 自身：按用户授权和当前分支约定处理；不要把 baseline 绑定成某个真实业务需求现场。
