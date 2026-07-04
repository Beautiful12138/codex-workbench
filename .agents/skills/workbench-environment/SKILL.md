---
name: workbench-environment
description: Use when Codex 需要读取或使用 codex-workbench 的 environments/ 环境资料，包括测试/生产环境、服务器、数据库/SQL、Redis、MQ、Nacos、GitLab、网站、账号密码、token、联调、部署、日志或外部系统操作方式。
---

# Workbench Environment

## 适用场景

使用本 skill 处理：

- 用户询问测试环境、服务器、数据库、Redis、MQ、Nacos、GitLab、网站、账号密码、token 或操作方式。
- 当前任务需要接口联调、外部系统访问、环境验证、部署检查或日志排查。
- evidence 需要说明验证使用了哪个环境。
- action note 需要记录外部环境操作目标、结果和回滚方式。

## 核心原则

`environments/` 是本地环境资料目录，里面的 Markdown 由用户和 AI 按实际项目自由组织，不要求固定字段，不由 CLI/schema 接管。

默认按测试环境资料理解；如果文档或用户明确指出 production、shared、customer、不可逆或会影响他人，按 `docs/policies/risk-and-process.md` 暂停确认或加严。

环境信息缺失时不要猜地址、账号、库名、namespace、token 或密码。缺失信息只能作为待确认问题、blocked 原因、partial evidence 或 action note 的未完成项。

对外回复、evidence 和 action note 中只写必要摘要，不复制长 token、完整密码、完整 auth header 或含密长日志。

## 读取顺序

1. 先看用户是否给了明确环境文件路径或名称。
2. 没有明确路径时，列出 `environments/` 下 Markdown 文件名，按项目、服务、环境名、服务器名或组件名匹配。
3. 读取最相关的 Markdown；必要时再读 `services/registry.yaml` 判断服务名和本地服务路径。
4. 涉及风险判断时读 `docs/policies/services-and-environment.md` 和 `docs/policies/risk-and-process.md`。
5. 涉及任务推进时回到 task YAML、task.md、working_scope、risk_triggers 和 validation/evidence 状态。

## 使用规则

- 只读查看环境资料不等于授权修改外部环境。
- 只读查看服务器、日志、进程、容器状态、配置当前值或端口，通常是只读探索或 ephemeral check。
- 修改服务器、容器、systemd、crontab、K8s、Nacos、DB、Redis、MQ、对象存储、权限、网络、镜像、部署参数或共享运行时状态，需要明确授权。
- 如果用户请求本身不是产品任务，但会改变外部环境，按 `docs/policies/action-routing.md` 处理为 maintenance_action 或 ops_action；外部持久变更应记录 action note，临时只读检查不默认落档。
- 如果环境操作支撑 task 验证，必须写真实 evidence；action note、口头判断或 doctor clean 不能替代 task evidence。

## 自动发现线索

看到以下词或相邻语义时，优先检查 `environments/`：

- 测试环境、dev、staging、uat、sandbox、预发、生产。
- 服务器、Linux、SSH、容器、K8s、Nacos、Redis、MQ、数据库、MySQL、PostgreSQL、对象存储。
- GitLab、仓库地址、网站、后台、控制台、管理端。
- 账号、密码、token、namespace、库名、端口、连接串。
- 联调、部署、重启、查看日志、查表、执行 SQL、验证接口。

## 输出边界

回答用户时优先说明：

- 找到了哪个环境资料文件。
- 相关入口是什么，必要时脱敏。
- 当前动作是只读、需要授权，还是需要 task/evidence/action note。
- 缺失哪些信息。
- 继续前是否需要用户确认。

不要把环境资料写入 `CURRENT.md`、generated views 或 task YAML 的长正文。task 只引用环境名称、文件路径或必要摘要。
