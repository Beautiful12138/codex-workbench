# 恢复与并发工作对象

本文件说明 Workbench 如何在多个 requirement、多个 task、多个 service 并存时选择工作对象。

## 核心原则

- 文件包是隔离单元，不是 Git 分支。
- `CURRENT.md` 是入口卡，不是单任务锁。
- `docs/generated/recovery.md` 是短恢复视图，不是状态真源。
- 包 YAML 是机器状态真源；Markdown 是解释层。
- 工作对象选择要保守、可解释、可恢复。

## 工作对象选择优先级

1. **显式路径优先**：用户给出 `docs/active/...`、任务包路径、需求包路径、服务路径或具体文件时，先读取该路径。
2. **显式 ID 优先于推断**：用户给出 `REQ-*`、`REQ-*-TASK-*`、`EV-*`、`ACT-*`、`CHG-*`、`DEC-*` 或 `SUS-*` 时，按 ID 找包或记录。
3. **用户语义匹配**：用户说“刚才那个任务”“这个需求”“某服务的问题”时，用 generated recovery 和相关包 YAML 对齐。
4. **generated recovery 辅助**：没有明确对象时，读取 `docs/generated/recovery.md`，优先看 active task、stage、next_step、service_refs、blocked 状态和 conflicts。
5. **无法唯一判断则暂停**：如果继续会写状态、改代码、推进阶段或得出完成结论，而对象仍不唯一，只问一个聚焦问题。

## 读取模式

### 恢复现场

先读 `AGENTS.md` 和 `CURRENT.md`，再读 `docs/generated/recovery.md`。如果 recovery 指向 active task，再读该 task 的 YAML 和 Markdown。

### 推进任务

必须读 task YAML。需要实现时还要读 task Markdown、服务登记和 implementation-ready。需要验证或 done 时还要读 evidence、validation 和 handoff。

### 需求梳理

读 material、discovery、intake 草案和 requirement YAML。没有用户确认前，不创建正式 task。

### 多任务切换

切换任务不是修改 `CURRENT.md` 的必需动作。只要用户明确目标，或 recovery 能唯一定位，就读取对应包继续。若需要跨会话长期接续，可更新 task `next_step` 或生成视图。

## recovery 视图应提供的信息

`docs/generated/recovery.md` 应尽量短，但要能帮助选择工作对象：

- active requirement 和 active task
- task stage
- next_step
- service_refs
- blocked 或 verification 状态
- 最近 evidence 摘要
- conflicts
- 超出显示上限时提示还有更多 active tasks

recovery 不应包含长正文、敏感原始材料或完整 evidence 输出。

## archive 与当前恢复

归档后的 requirement/task 是冷历史。默认恢复现场时不展开 archive；只有用户查询历史、需要恢复旧版本、或执行 archive action 时读取。

generated index 可以列 archive 摘要，但 recovery 默认聚焦 active 工作。

## 服务并发

一个 task 可以关联多个 service，一个 service 也可以被多个 task 使用。`service_refs` 只帮助恢复上下文，不限制只读探索，也不是修改白名单。

如果发现任务实际需要新服务：

1. 只读探索可以继续。
2. 修改前要确认服务是否应登记。
3. 登记后再让 task 的 service context 或 working_scope 体现该服务。

## 冲突处理

常见冲突：

- requirement `task_refs` 指向不存在的 task。
- task `requirement_id` 与 requirement `task_refs` 不一致。
- task id 未使用所属 requirement id 作为前缀。
- task 引用未知 service。
- task validation 指向不存在或不匹配的 evidence。
- generated view stale。
- archive manifest 无效。

冲突不按更新时间静默覆盖。能只读报告就报告；会影响阶段推进、归档或修改授权时，先解决或让用户确认风险。
