# 动作分流

本文件说明用户请求进入 Workbench 后先如何分类。它是温路径，只在需要落状态、推进任务或判断是否需要记录时读取。

## 默认原则

- 普通讨论、解释、方案判断和只读探索默认不写状态。
- 只有用户明确要求纳入、创建、更新、验证、关闭或归档时，才进入对应 CLI 或包写入。
- 不确定性不影响只读调查时，先调查；不确定性会影响真实修改、环境、数据、权限或完成结论时，先暂停确认。

## 类型

| 类型 | 何时使用 | 记录方式 |
| --- | --- | --- |
| `discussion` | 方向讨论、解释、比较 | 不落档 |
| `read_only_exploration` | 看文件、看服务状态、看生成视图 | 通常不落档；支撑需求时写 discovery |
| `product_task` | 用户确认要实现的需求或任务 | material / discovery / intake / task / evidence |
| `maintenance_action` | 工具维护、文档整理、一次性本地动作 | 必要时写 action note |
| `ops_action` | 外部环境、权限、配置、运行状态等持久操作 | 先确认授权；必要时写 action note |
| `ephemeral_check` | 一次性只读检查、状态确认、临时诊断 | 通常不落档；支撑后续判断时写 discovery 或 action note |
| `archive_action` | 版本归档或历史整理 | 需要需求关闭确认和独立归档授权 |

## 不升级规则

- 用户只是在当前任务内补充小范围文案、命名、说明或局部验证时，不自动新建任务。
- action note 不替代 evidence，不支撑 `validation.status=passed`。
- action note 的 `action_type` 只接受 `maintenance_action`、`ops_action`、`ephemeral_check`；`product_task` 必须走正式 task。
- action note 的 `status`、`authorization`、`target` 和 `result` 只记录非任务动作上下文，不能替代 evidence、validation 或用户验收。
- `archive_action` 是路由分类，不是 action note 的 `action_type`。
- 维护或归档动作如果会改变外部环境、共享状态、权限、配置或运行状态，先按 `services-and-environment.md` 确认授权边界。
- `implementation_adjustment` 不等于正式 `scope_change`；`scope_clarification` 用于对齐口径但默认不写正式 change record；改变目标、验收、契约、外部系统或真实后果才写 change record。
