# CURRENT

role: 入口卡
workspace: codex-workbench 基线
workspace_status: baseline
service_registry: services/registry.yaml
generated_views: docs/generated/
active_packages: docs/active/
updated_at: 2026-06-30

## 从这里开始

这个仓库根目录同时是 Workbench 基线工作空间和 Python 包仓库。

这个文件只作为入口卡使用。启动时先读 `AGENTS.md`，再读本文件；工作对象应从用户请求、生成的恢复视图、CLI 参数或明确的包路径中选择。

## 基线状态

- 尚未登记真实需求。
- 尚未登记真实任务。
- 尚未登记真实服务路径。
- `docs/policies/` 是温路径地图，只在对应动作触发时读取。
- `docs/archive/` 是冷路径历史，只在查询、生成索引或版本归档时读取。

## 下一步

- 普通讨论或只读探索：不写状态，按用户问题读取最少文件。
- 登记真实需求：先走 material / discovery / intake，用户确认 readable 后再创建任务。
- 推进任务：从 `docs/generated/recovery.md` 或明确包路径进入任务包，再按任务范围和 evidence 推进。
- 开发 Workbench 自身：按用户请求、明确任务包或当前分支约定选择工作对象；不要把 baseline 绑定到某个构建现场。
