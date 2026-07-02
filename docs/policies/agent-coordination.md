# Agent 协作

本文件说明 Codex、skills 和子代理如何协作，目标是减少漂移，而不是增加仪式。

## Skills

- `.agents/skills/workbench-*` 是短提示，用于恢复、任务推进、验证交接和归档。
- skill 不替代 `AGENTS.md`、task 包、CLI、evidence 或用户确认。
- skill 不应注入长 policy；需要细节时读 `docs/policies/*`。

## 子代理

- 子代理适合做只读复核、并行检查、文档连贯性审查和风险扫描。
- 子代理结论不是事实真源；主代理需要读输出、核对文件和验证命令。
- 高风险或真实后果任务不得自写自审通过，应有独立复核或用户确认。

## 协作边界

- 不为了流程完整而创建空 review、空 evidence 或空 change。
- 不把普通讨论污染成正式状态。
- 需要阶段推进、验证完成、需求关闭或归档时，必须回到包真源和 CLI。

## 接续

- 新窗口先读 `AGENTS.md` 和 `CURRENT.md`。
- 如果 `CURRENT.md` 指向 active package，再读对应 YAML/Markdown。
- 生成视图可帮助定位，但不能覆盖包真源。
