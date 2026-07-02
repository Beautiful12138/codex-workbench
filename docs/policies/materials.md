# 材料与需求事实

本文件说明原始材料如何进入 Workbench，避免把未确认信息升级成开发事实。

## 材料

- material 保存来源、标题、接收时间和脱敏摘要。
- 原件默认不复制、不提交；路径、链接或敏感内容只在用户明确允许时记录。
- material 只证明“收到过这个输入”，不证明需求已经确认。

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
