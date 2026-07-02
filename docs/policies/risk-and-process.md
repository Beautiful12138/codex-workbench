# 风险与流程档位

本文件说明 Workbench 如何判断任务风险和流程显性化强度。核心原则：风险按真实后果判断，不按组件名判断。

## 风险函数

风险由实际动作和后果决定：

```text
risk = f(action, environment, blast_radius, reversibility, data_sensitivity)
```

不要使用：

```text
risk = f(component_name)
```

DB、SQL、Redis、MQ、Docker、配置文件、多模块、脚本、依赖升级和中间件都是复杂度信号，不天然等于高风险。真正决定是否升级的是：做了什么、在哪个环境、影响谁、是否改真实数据、是否可回滚、是否改变契约或权限、是否能验证。

## impact_profile

`task.yaml` 可使用 `impact_profile` 记录影响面画像。它解释 `risk_level` 和 `process_level` 为什么这样选择，但不替代 review、implementation、evidence 或用户确认。

建议字段：

```yaml
impact_profile:
  action: code_change | config_change | data_read | data_write | schema_change | deployment | environment_operation | documentation | analysis
  component_signals:
    - code
    - sql
    - database
    - config
  environment: local | sandbox | personal | shared | production | unknown
  data_effect: none | read_only | test_data_write | real_data_write | schema_or_migration | destructive
  external_effect: none | read_only | write | deploy | notify | cost | security
  blast_radius: self | single_service | multi_service | shared_users | external_users | unknown
  reversibility: git_revert | easy_manual | backup_restore | hard | irreversible | unknown
  contract_change: false | true | unknown
  security_or_permission: false | true | unknown
  verification_confidence: local_testable | integration_required | manual_acceptance_required | unclear
```

字段说明：

- `action`：本任务主要动作。
- `component_signals`：出现的技术组件线索，只用于提醒和恢复，不直接决定风险等级。
- `environment`：目标环境。未知环境不能当成本地环境处理。
- `data_effect`：对数据的实际影响。
- `external_effect`：是否影响外部系统、通知、费用、部署或安全。
- `blast_radius`：影响半径。
- `reversibility`：失败后恢复难度。
- `contract_change`：是否改变公开接口、跨服务契约、消息格式、schema、索引或验收口径。
- `security_or_permission`：是否涉及权限、认证、安全、密钥、token、账号或隐私。
- `verification_confidence`：验证路径是否清楚。

## risk_level

`risk_level` 表达真实后果风险：

- `low`：本地、可验证、可回滚、无真实数据和外部影响。
- `standard`：正常工程修改，影响面清楚，可验证，可回滚；可能改变业务行为，但不触发真实后果红线。
- `high`：涉及真实后果、高不确定性、共享状态、跨服务影响、契约变化、环境写入或复杂回滚。
- `critical`：生产、真实数据破坏、权限安全、不可逆操作、影响他人、费用、外部通知或重大业务后果。

不能仅凭“改动小”把真实后果任务降级。风险降级必须来自明确事实或用户确认。

## process_level

`process_level` 表达流程显性化强度，不降低安全语义：

- `micro`：非常小、低风险、可本地验证、可 git 回滚；不建厚文档。
- `lightweight`：小范围真实任务；需要 task、prepare、evidence，review / implementation 可内联。
- `standard`：正常工程任务；需要清楚 scope、implementation-ready、验证和回滚。
- `high`：需要显性 review、implementation ref、risk_triggers 和风险接受。
- `critical`：必须暂停确认，强门禁，必要时独立复核。

`process_level=micro/lightweight` 只表示少文件、少仪式，不表示可以跳过目标、范围、验证、交接和完成 guard。

## 必须升级或暂停

无论组件名是什么，出现以下情况时必须升级或暂停确认：

- 真实数据写入、删除、迁移、清空。
- 生产环境、共享环境、外部服务或影响他人的运行时状态。
- 部署、发布、重启线上服务、配置中心发布。
- 权限、认证、安全、密钥、token、账号、隐私。
- 支付、短信、邮件、通知、费用。
- 不可逆或难以回滚操作。
- 对外接口、跨服务契约、消息格式、schema、索引或验收口径变化。
- 验证路径不清、环境不清、授权不清或回滚不可执行。

## 不自动升级

以下情况不应因为组件名自动进入重流程：

- 只读查看代码、配置、日志、schema 或状态。
- 本地 mock、本地测试、本地可重置数据。
- 文档 SQL、示例配置、测试 fixture。
- 当前任务范围内的命名、注释、局部日志、文案、小验证补充。
- 可 git 回滚、无真实外部影响、无契约变化的小改动。

不自动升级不等于无记录。只要进入正式 task，仍要保留目标、范围、验证、回滚和 evidence。

## 示例判断

同样是 SQL：

- 本地单测 SQL 或 mock SQL：通常 `risk_level=low`，`process_level=micro/lightweight`。
- 业务查询 SQL 小改，影响接口返回：通常 `risk_level=standard`，`process_level=standard/lightweight`。
- 生产库 DDL、迁移、批量 update/delete：必须 `risk_level=high/critical`，需要 review、implementation、risk acceptance、evidence 和回滚锚点。

同样是配置：

- 本地开发配置或示例配置：通常低风险。
- 服务运行配置，影响真实接口或共享环境：至少 standard。
- 生产配置中心发布、权限或密钥变化：high/critical。

同样是脚本：

- 只读诊断脚本：通常低风险或 action note。
- 本地可 git 回滚的开发便利脚本：通常 maintenance_action。
- 批量删除、迁移、发布、重启、改权限脚本：high/critical 或 ops_action，先确认授权和回滚。

## CLI 门禁边界

AI 负责根据上下文填写 `impact_profile`、`risk_level`、`process_level` 和 `risk_triggers`。CLI/schema 负责结构化校验和硬门禁：

- task 创建后发现影响面变化，用 `task impact-set` 更新风险画像；该命令必须记录更新原因。
- `task prepare` 可以在开工准入时同步补齐或修正 `impact_profile`、`risk_level` 和 `process_level`。
- high / critical 进入 `in_progress` 前必须有 review、implementation ref、working_scope、risk_triggers 和风险接受。
- high / critical 进入 `in_progress` 前必须有 `impact_profile`。
- 明显真实后果字段不能与 `risk_level=low` 或 `process_level=micro` 同时出现。
- 环境、授权、验证或回滚不清时，不能用 task stage 推进掩盖缺口。
- generated views 只展示风险摘要和缺口，不复制长正文。

CLI 不做复杂业务自动评分器，也不能因为 `component_signals` 中出现某个组件名就自动判高风险。`doctor check` 只报告机器真源和 lifecycle 的硬问题，不做启发式风险扫描；风险缺口主要通过 `task check`、`CURRENT.md`、`docs/generated/index.md` 和 `docs/generated/recovery.md` 暴露。
