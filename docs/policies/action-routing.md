# 动作分流

本文件说明用户请求进入 Workbench 后如何分类。分类决定读取深度、是否写状态、用哪个 CLI、何时暂停。

## 总原则

- 普通讨论、解释、方向判断和只读探索默认不写状态。
- 用户明确要求纳入、创建、推进、验证、关闭、归档或记录时，才写包或运行状态变更 CLI。
- 能只读调查就先调查；会影响代码、配置、数据、权限、安全、部署、外部环境或完成结论时，先确认。
- 低风险小动作不需要制造空仪式；高影响动作不能靠猜。
- 风险按真实后果判断，不按 DB、SQL、Redis、MQ、配置、部署等组件名判断；完整判断见 `docs/policies/risk-and-process.md`。

## 类型判断

| 类型 | 使用场景 | 默认记录 |
| --- | --- | --- |
| `discussion` | 解释、比较、判断方向、问是否合理 | 不落档 |
| `read_only_exploration` | 看文件、看状态、看日志、定位问题 | 通常不落档；支撑需求时写 discovery |
| `product_task` | 用户确认要实现、修复或调整交付目标 | material / discovery / intake / task / evidence |
| `maintenance_action` | Workbench 自身维护、文档整理、本地工具修补 | 必要时写 action note |
| `ops_action` | 环境、权限、配置、部署、运行状态、外部持久变更 | 先确认授权；必要时写 action note |
| `ephemeral_check` | 一次性只读检查、临时诊断、状态确认 | 通常不落档；支撑后续判断时写 discovery 或 action |
| `archive_action` | requirement close、archive preflight、archive version、历史查询 | close 确认和 archive 授权分开 |

## 判断细则

### discussion

用户在问“怎么看”“是否合理”“帮我分析”“解释一下”时，默认是 discussion。可以读用户指定文件或少量上下文，但不写状态。

只有用户明确说“纳入需求”“按这个改”“创建任务”“记录下来”时，才升级。

### read_only_exploration

用户说“看看”“定位”“查一下”“读一下日志/配置/代码”时，默认只读探索。可以使用搜索、读取文件、运行只读命令。探索结果如果会成为需求事实，应写 discovery；否则不落档。

### product_task

用户明确要实现、修复、修改可交付行为，或要求推进某个 requirement/task 时，进入产品任务流。产品任务不能用 action note 替代。

原始材料和 AI 推断不是可开发事实；必须经过 intake 并由用户确认后，才成为 readable requirement。

创建 task 时应写清 `risk_level`、`process_level`、`risk_triggers`，必要时写 `impact_profile`。组件名只作为线索；真实数据、生产/共享环境、权限、安全、部署、不可逆、影响他人或验证/回滚不清时，按风险 policy 加严或暂停。

### maintenance_action

修改 Workbench 自身文档、模板、测试或 CLI，且不绑定真实业务需求时，可作为维护动作处理。若改动需要跨会话接续、影响使用方式或需要留痕，可写 action note；否则用 Git 提交即可。

### ops_action

任何外部环境、服务器、容器、权限、配置、部署、共享状态或运行时状态变更，都属于 ops_action。即使用户语气很轻，也要先确认目标、环境、授权和回滚方式。

Standalone ops action 不因为风险高就自动变成产品 task；但真实后果风险仍必须按 `risk-and-process` 加严授权、记录和回滚。

### ephemeral_check

一次性检查通常不写状态。若检查结论将支撑需求、验收、风险接受或运维判断，再转为 discovery 或 action note。

### archive_action

归档不是普通 action note。归档前必须有 requirement closure；archive authorization 是独立确认，不能用用户验收或需求关闭替代。

## 不升级规则

- 当前任务内的小范围命名、注释、文案、局部验证调整，不自动新建任务。
- `implementation_adjustment` 不等于正式范围变更。
- `scope_clarification` 用于口径对齐，默认不写 change record。
- 改变目标、验收、公开契约、数据结构、外部系统或真实后果时，写 change record。
- action note 的 `status`、授权、目标和结果只记录非任务动作上下文，不能替代 evidence、validation 或 handoff。

## 停止点

遇到以下情况暂停确认：

- 工作对象无法唯一判断，且继续会写状态或改文件。
- 需求目标、验收、范围、服务、环境、权限或数据影响不清。
- 触发 task 的 `risk_triggers`。
- 用户要求外部持久变更但授权、环境或回滚不清。
- 用户只是讨论方向，但继续需要创建 task 或写状态。
