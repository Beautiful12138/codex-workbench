# 材料与需求事实

本文件说明原始材料如何进入 Workbench，避免把未确认信息升级成开发事实。

## 材料

- material 保存来源、标题、接收时间和脱敏摘要。
- 原件默认不复制、不提交；路径、链接或敏感内容只在用户明确允许时记录。
- material 只证明“收到过这个输入”，不证明需求已经确认。

## 轻量材料和说明

- `docs/materials/` 存放外部或用户提供内容的搬迁/收集副本，例如导出的文档、会议纪要、接口摘录或临时资料，尽量保留原始语义。
- `docs/briefs/` 存放 Codex 基于项目、需求、代码或材料生成的解释型文档，例如架构说明、流程梳理、需求解读、总结或上手指南。
- 这两个目录不需要结构化状态，也不自动进入 material / discovery / intake；只有用户要求纳入需求、支撑验收或需要长期跟踪时，才转成对应记录。
- 目录内内容是解释层和资料层，不能覆盖代码、配置、服务登记、task/evidence 或用户确认。

## Discovery

- discovery 记录只读探索得到的系统观察、AI 推断、假设和待确认问题。
- 系统观察必须来自文件、命令、日志、服务状态或用户明确说明。
- AI 推断不得写成 confirmed facts。

## Intake

- intake 把材料和 discovery 转成 AI-readable 需求草案。
- 用户确认后才能成为 readable requirement。
- intake 的 acceptance 和 non-goals 是后续 task 拆解的边界来源。

## 读取边界

- 普通讨论不需要默认展开全部材料。
- 创建任务、评估范围变化或验证需求关闭时，才回读 intake 和相关 discovery。
