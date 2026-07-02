# 工作空间地图

这个仓库有两个角色：

- Codex 运行时使用的基线工作空间。
- Workbench 工具的 Python 包源码。

入口文件的关系：

- `AGENTS.md`：入口地图，说明启动读取顺序、动作分流、状态真源、事实层级、policy 地图、skills、自动提醒和健康检查边界。
- `CURRENT.md`：当前入口卡，只保存 baseline 或当前工作对象的第一眼恢复信息。
- `README.md`：人类使用说明和主路径。
- `pyproject.toml`：包元数据和依赖策略。

## 运行时目录

- `docs/active/`：当前 requirement、task、evidence、handoff 等包；包 YAML 是机器状态真源，Markdown 是解释层。
- `docs/inbox/`：尚未成熟的材料入口。
- `docs/generated/`：从包 YAML 生成的 index 和 recovery 视图；可重建，不覆盖真源。
- `docs/archive/`：版本化归档；默认冷路径，只在查询、生成索引或恢复历史时读取。
- `docs/policies/`：温路径策略地图，只在对应动作触发时读取。
- `services/`：服务登记和只读状态输入；服务登记帮助恢复上下文，不接管外部仓库 Git 生命周期。

## 工具目录

- `src/codex_workbench/`：Python 包源码。
- `tests/`：CLI、模型、模板、doctor、归档、hooks 和 dogfood 回归测试。
- `.codex/`：Codex hook 配置和只读短提醒脚本。
- `.agents/skills/`：Workbench 本地技能，按需恢复、推进、验证和归档。
- `templates/`：后续包和基线模板材料。

## 工作流关系

1. 普通讨论和只读探索只读最少文件，不默认写状态。
2. 真实需求先走 `material`、`discovery`、`intake`；用户确认 readable 后才能创建正式 task。
3. 任务推进以 `docs/active/<task>/task.yaml` 和 `task.md` 为中心。
4. 验证结论必须来自 `evidence`，用户交接状态写入 `handoff`。
5. 需求关闭和归档是两个独立确认：关闭不等于授权归档。
6. 生成视图和自动提醒只帮助恢复，不替 AI 或 CLI 做阶段判断。
