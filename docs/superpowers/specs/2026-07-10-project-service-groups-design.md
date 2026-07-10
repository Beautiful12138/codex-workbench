# Workbench 项目服务分组设计

## 背景

`services/registry.yaml` 当前只登记扁平服务。对于 `studioV3` 这类包含二十多个独立服务仓库的项目，存在两个问题：

- 把项目根目录登记成一个服务会丢失子服务边界。
- 把所有子服务分别登记后，`workspace context` 无法表达它们属于同一个项目。

当前 `workspace context` 已限制默认服务详情数量，但缺少项目层级。目标不是增加更多默认详情，而是让第一眼输出先表达项目归属，并完整展示轻量的服务名称。

## 目标

- 为已登记服务增加可选项目分组，不改变服务作为任务引用单位的语义。
- `workspace context` 默认按项目分组，全量展示服务名称。
- 默认项目概览不展示服务路径、用途、备注、Git 状态或入口候选。
- 支持只查看指定项目，并继续通过现有服务上下文查看单个服务详情。
- 保持旧版 `registry.yaml`、现有服务名和 `service_refs` 兼容。

## 非目标

- 不扫描项目根目录，不自动发现或批量登记 Git 子仓库。
- 不复制、克隆、移动或接管服务仓库。
- 不引入嵌套的项目 registry，也不登记没有服务的空项目。
- 不允许不同项目复用相同的服务名；服务名继续全局唯一。
- 不改变 task、requirement、evidence、archive 或 generated view 的生命周期语义。
- 不引入新运行时依赖。

## 方案比较

### 方案一：服务增加可选 `project` 字段（采用）

每个 `ServiceEntry` 可选记录项目名，项目概览由 registry 中的服务动态归组。旧服务没有该字段时归入“未分组”。

优点是兼容现有扁平 registry、服务查找和 `service_refs`，改动范围集中；缺点是项目没有独立元数据，且服务名仍需全局唯一。第一版只需要分组导航，这个限制可接受。

### 方案二：引入嵌套项目模型

在 registry 中增加一等 `projects`，项目下再嵌套服务。该结构能表达项目根目录和项目元数据，但会改变服务查找、task 引用、迁移和写入器边界，超出本次需求。

### 方案三：根据服务名或路径推断项目

通过名称前缀或共同父目录推断分组，不修改 schema。该方案无法稳定表达用户意图，目录移动或命名变化后容易产生错误分组，因此不采用。

## 数据模型

`ServiceEntry` 增加可选字段：

```yaml
services:
  - name: algorepo
    project: studioV3
    local_path: D:\\Work\\studio-pass-rebuild-workspace\\studioV3\\algorepo
```

约束如下：

- `project` 使用与服务名相同的非空字符串校验；缺失表示未分组。
- `ServiceRegistry.schema_version` 保持 `0.1`。新增字段是向后兼容的可选字段，旧 registry 无需迁移。
- 服务 `name` 仍是全局唯一标识；项目名不参与服务身份计算。
- task 的 `service_refs` 继续引用服务 `name`，不接受项目名，也不动态展开项目成员。
- 项目顺序按其在 registry 中首次出现的顺序；项目内服务保持 registry 顺序，保证输出稳定。

## CLI 写入接口

`service add` 增加可选参数：

```powershell
codex-workbench service add algorepo --path <path> --project studioV3
```

`service update` 增加：

```powershell
codex-workbench service update algorepo --project studioV3
codex-workbench service update algorepo --clear-project
```

规则如下：

- `--project` 设置或更换项目。
- `--clear-project` 把服务移入“未分组”。
- 两个参数同时出现时返回 validation error，退出码为 `2`，不写 registry 或 generated views。
- 未提供二者时保持原项目值不变。
- 所有 registry 写入继续通过现有原子写入器完成，并保持 `--dry-run` 行为。

`service context` 的文本和 JSON 输出增加项目信息；未分组时文本显示“项目：未分组”，JSON 的 `project` 为 `null`。`service status` 保持现有机器摘要不变。

## Workspace Context 展示

默认输出增加登记项目数量，并用“项目与服务概览”代替当前逐服务详情概览：

```text
登记项目：1
登记服务：26

## 项目与服务概览

- studioV3：23 个服务
  - algorepo
  - analyticspolicy
  - apipkg
  - cognitivesvc-kestrel
  - data-stream-handler
  - dataSync
  - device
  - engine-struct-db
  - eventhandler
  - frontend
  - guns
  - library
  - map
  - person
  - person-flow-anlysis-agg
  - policy-control
  - scenetemplate
  - sensebiAdapter
  - sensestudio
  - senseyeXAdapter
  - systemconfighandler
  - utility
  - vt2

- 未分组：3 个服务
  - sensetime-city-agent-office-raccoon
  - sensetime-city-agent-harness
  - sensetime-city-agent-raccoon-console
```

真实输出必须全量列出该项目的所有服务名称，不截断、不显示 `and N more services`。

默认概览不输出服务路径、用途、备注、Git 状态、入口候选和每服务任务引用数。活动任务引用了未登记服务时，仍单独展示“未登记服务引用”，避免分组展示掩盖硬缺口。

`workspace context` 增加可选过滤参数：

```powershell
codex-workbench workspace context --project studioV3
codex-workbench workspace context --ungrouped
```

指定项目时只展示该项目的服务名称；`--ungrouped` 只展示未分组服务。两个参数同时出现时返回 validation error，未知项目返回 `unknown_project`，退出码均为 `2`。`--task` 和 `--service` 的嵌入行为保持不变。

## 深入检查

`--check-services` 仍是显式的重检查入口，但不能因为默认全量展示名称而自动检查全部服务：

- 不带 `--project` 时，继续按现有优先级最多检查 5 个服务。
- 带 `--project` 时，只在该项目内按 registry 顺序最多检查 5 个服务。
- 深入结果放在独立的“服务检查”小节，项目概览仍保持纯名称列表。
- 其余服务通过 `workspace context --service <name>` 或 `service context <name>` 点名检查。

这样既保留现有负载边界，也避免把名称列表与路径、Git 和入口详情混在一起。

## 兼容性

- 旧 registry 缺少 `project` 时继续通过 schema 校验，并全部显示在“未分组”。
- 现有 `service add/update/delete/list/status/context` 命令名称保持不变。
- `service_refs`、服务唯一性、路径解析和 Git 检查逻辑保持不变。
- `workspace context` 的服务概览文本会有意变化；依赖旧文本的测试和文档需要同步更新。
- generated views 继续从同一 registry 读取服务；第一版不要求 generated views 按项目分组。

## 错误处理

- 空白项目名由模型校验拒绝。
- `--project` 与 `--clear-project` 冲突时，在任何写入前失败。
- `workspace context --project` 找不到项目时返回结构化 `unknown_project` 错误。
- registry 中未知字段、重复服务名和并发写冲突继续沿用现有校验及错误语义。

## 测试策略

按测试驱动顺序覆盖：

1. 模型测试证明旧 registry 仍可读取，新 registry 可保存 `project`，空白项目名被拒绝。
2. 服务写入测试覆盖 `service add --project`、`service update --project`、`--clear-project`、冲突参数和 dry-run。
3. 服务上下文测试覆盖文本与 JSON 的项目字段。
4. Workspace context 测试构造 23 个分组服务，验证名称全部出现且路径、用途、备注和 Git 详情不出现。
5. Workspace context 测试覆盖多个项目、未分组、项目过滤、未知项目和未登记活动引用。
6. 深入检查测试验证全局和指定项目都最多检查 5 个服务，且详情位于独立小节。
7. 运行完整 pytest、Ruff、CLI help、schema 和 Git diff 检查。

## 文档更新

同步更新以下使用边界：

- `docs/policies/services-and-environment.md`：项目分组、默认概览和深入检查负载。
- `.agents/skills/workbench-cli/SKILL.md`：`--project`、分组导航和服务写入参数。
- `AGENTS.md`：默认导航路径仍保持不变，只补充项目概览是轻量入口。
- CLI help 与相关测试中的示例输出。

## 交付与 Git 边界

- 实现在 `D:\\Work\\codex-workbench-main` 的 `codex/project-service-groups` 分支进行。
- 完成本地实现和验证后先交给用户检查，不推送远端。
- 只有用户明确确认后才推送功能分支。
- 推送完成后，再经用户授权把结果合并到 `D:\\Work\\codex-workbench` 的本地目标分支。

## 完成条件

- 可通过 CLI 为服务设置、变更和清除项目分组。
- 默认 `workspace context` 按项目全量列出服务名称，不展示服务细节。
- 可按项目过滤概览，单服务详情入口保持可用。
- 默认和按项目的深入检查都保持最多 5 个服务的负载边界。
- 旧 registry 和现有 task `service_refs` 无需迁移。
- 相关测试、完整测试套件和 Ruff 通过。
- 用户确认前没有远端 push，也没有合并到 `D:\\Work\\codex-workbench`。
