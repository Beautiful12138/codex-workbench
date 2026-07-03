# 恢复与并发工作对象

本文件说明 Workbench 如何在多个 requirement、多个 task、多个 service 并存时选择工作对象。

## 核心原则

- 文件包是隔离单元，不是 Git 分支。
- `AGENTS.md` 是稳定入口规则卡。
- 日常恢复默认路径是 `workspace context -> task context -> service context -> task package`。
- `CURRENT.md` 是 CLI 生成的最近工作面板，不是单任务锁。
- `docs/generated/index.md` 是完整活动目录，不是状态真源。
- `docs/generated/recovery.md` 是续接和异常队列，不是状态真源。
- 包 YAML 是机器状态真源；Markdown 是解释层。
- 工作对象选择要保守、可解释、可恢复。
- 名称优先：需求/任务 ID 是内部锚点，默认不向用户暴露；用户回复和 generated views 的主展示应优先使用名称。
- 等待反馈是正常等待，不是阻塞。`verification_pending` 或 `handoff.status=waiting_user_validation` 应轻量展示，等待用户、测试环境或外部系统回传结果。

## 工作对象选择优先级

1. **显式路径优先**：用户给出 `docs/active/...`、任务包路径、需求包路径、服务路径或具体文件时，先读取该路径。
2. **名称和自然指代优先**：用户说任务名、需求名、“刚才那个任务”或“这个需求”时，先用 generated views 定位；选中 task 后优先用 `task context` 对齐现场。
3. **显式 ID 精确定位**：用户给出 `REQ-*`、`REQ-*-TASK-*`、`EV-*`、`ACT-*`、`CHG-*`、`DEC-*` 或 `SUS-*` 时，按 ID 找包或记录。
4. **generated views 辅助**：没有明确对象时，先看 `workspace context`；仍不够时再看 `CURRENT.md` 最近活动、`docs/generated/recovery.md` 的续接队列和异常；需要完整目录时读 `docs/generated/index.md`。
5. **无法唯一判断则暂停**：如果继续会写状态、改代码、推进阶段或得出完成结论，而对象仍不唯一，用名称、阶段、服务和最近更新时间问一个聚焦问题。

## 读取模式

### 恢复现场

先读 `AGENTS.md`，再运行 `workspace context`。如果已能定位 active task，先用 `task context <任务名或ID>` 看当前工作面；若仍不清楚，再读 `CURRENT.md`、`docs/generated/recovery.md` 或 `docs/generated/index.md`。需要细节、写状态或处理门禁时，再读 task YAML 和 Markdown。

### 推进任务

先用 `task context` 判断当前能做什么、缺什么、关联服务是否可接。需要写状态、prepare、调整风险画像或推进阶段时，必须读 task YAML；需要实现时还要读 task Markdown、服务 context 和 implementation-ready；需要验证或 done 时还要读 evidence、validation 和 handoff。

### 需求梳理

读 material、discovery、intake 草案和 requirement YAML。没有用户确认前，不创建正式 task。

### 多任务切换

切换任务不是手改 `CURRENT.md` 的理由。只要用户明确目标，或 generated views 能唯一定位，就先用 `task context` 接住对应任务现场；需要写状态、实现细节或门禁判断时，再读对应包继续。若需要跨会话长期接续，优先更新 task `next_step`、evidence、action、change、decision 或 suspicion，再由 CLI 刷新生成视图。

## recovery 视图应提供的信息

`CURRENT.md` 应限制展示范围，只展示最近更新的有限数量活动任务；`docs/generated/index.md` 可列完整活动目录；`docs/generated/recovery.md` 应聚焦续接和异常：

- 需要续接的 active requirement 和 active task
- task stage
- next_step
- service_refs
- 等待反馈，例如 `verification_pending` 或 `waiting_user_validation`
- blocked 状态
- 最近 evidence 摘要
- conflicts
- generated view stale 或真源冲突

generated views 不应包含长正文、敏感原始材料或完整 evidence 输出。

## archive 与当前恢复

归档后的 requirement/task 是冷历史。默认恢复现场时不展开 archive；只有用户查询历史、需要恢复旧版本、或执行 archive action 时读取。

generated index 可以列 archive 摘要，但 current 和 recovery 默认聚焦 active 工作。

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
