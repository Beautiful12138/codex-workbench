# Agent 协作

本文件说明 Codex、skills、CLI、子代理和用户如何协作。

## 基本分工

- `AGENTS.md`：热路径入口和最高频判断。
- `CURRENT.md`：CLI 生成的最近工作面板。
- policy：运行规则和反例。
- skills：可执行操作规程。
- CLI/schema：可靠写入和门禁。
- generated views：最近工作、完整活动目录、续接和异常检索。
- 用户确认：需求、范围、风险、验收、关闭和归档的高层事实来源。

## skills

使用本仓库 `.agents/skills/workbench-*`，不要默认到其他仓库找同名 skill。

skill 不替代包 YAML、evidence、CLI 或用户确认。skill 应告诉 Codex 怎么读、怎么判断、什么时候停、用哪个命令。

## 子代理

子代理适合：

- 只读复核。
- 并行检查多个服务。
- 文档连贯性审查。
- 风险扫描。
- 测试失败定位。

子代理结论不是事实真源。主代理必须核对文件、命令输出和状态包。

高风险、critical 或有真实后果的任务，不应由同一主体自写自审通过；需要独立复核或用户确认。

## 接续

新窗口先读 `AGENTS.md`，再运行 `workspace context`。若选择到 task，先用 `task context` 看轻量工作面；若涉及服务，先用 `service context` 看真实路径和 Git 粒度。需要完整活动盘点时，再读 `CURRENT.md`、`docs/generated/recovery.md` 或 `docs/generated/index.md`；需要写状态、推进阶段、验证或归档时，再读对应 task YAML/Markdown、evidence、handoff、policy。

不要把旧聊天摘要覆盖状态真源。旧摘要只能作为线索。

## 不制造仪式

- 不为普通讨论创建 task。
- 不为只读探索默认写状态。
- 不预生成空 review、implementation、evidence 或 change。
- 不让 doctor、hook 或 generated view 自动推进阶段。

需要长期接续时，优先写入真实 task `next_step`、evidence、action、change、decision 或 suspicion，再由 CLI 刷新 `CURRENT.md` 和 generated views。
