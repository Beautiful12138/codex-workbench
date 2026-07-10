# Workbench 大文件拆分与测试隔离设计

## 背景

当前测试套件已经覆盖 CLI、状态模型、包写入、索引生成和端到端流程，但存在两个维护问题：

- `tests/test_cli.py` 超过 5,000 行，测试职责集中，定位和局部修改成本较高。
- `src/codex_workbench/index.py` 与 `src/codex_workbench/packages.py` 同时承载多类职责，继续增长会增加修改时的上下文负担。

此外，先前的 registry 测试失败暴露出单元测试读取仓库真实状态并断言可变内容的问题。本次先完成耦合审计，再进行保守拆分。

## 目标

- 保持 CLI 命令、公开 Python 导入、YAML/Markdown 格式、生命周期门禁和错误语义不变。
- 将 CLI 测试按命令域拆分，使每个测试文件聚焦一个稳定职责。
- 将索引逻辑拆为记录加载、冲突检测、视图渲染和公共入口。
- 将任务包逻辑拆为公共入口、公共支撑、包创建和任务变更。
- 将真实仓库资产检查与纯单元测试分离。
- 通过结构约束测试防止大文件重新无界增长。

## 非目标

- 不改变命令名称、参数、输出文本或退出码。
- 不改变状态模型、schema 版本、生成视图内容或文件布局。
- 不重写生命周期、风险判断、验证或归档规则。
- 不引入新运行时依赖。
- 不顺带处理与拆分无关的代码风格或业务逻辑问题。

## 审计结论

### 需要修正的耦合

`tests/test_models.py` 中的 registry 模型测试读取真实 `services/registry.yaml`。即使断言已经改为动态内容，它仍把单元测试与仓库资产绑定。该测试应改用内联的非空 registry 数据。

仓库自身的 registry 仍应被验证，但应放在 `tests/test_codex_integration.py` 中，只断言文件能够通过 `ServiceRegistry` schema 校验，不断言服务数量、名称、路径或说明。

### 有意保留的仓库契约

- hooks 配置与脚本由 `tests/test_codex_integration.py` 验证，这是明确的仓库集成契约。
- CLI 入口薄层检查读取 `src/codex_workbench/cli.py`，这是有意的结构约束。
- `tests/golden/` 是稳定测试夹具，不属于运行时真实状态。
- 其余工作区读写测试均使用 `tmp_path` 构建隔离工作区。

## 目标模块结构

### CLI 测试

共享构造器和断言迁移到 `tests/cli_test_support.py`，并由以下测试文件按命令域复用：

- `test_cli_core.py`：版本、schema、workspace、index、workspace root。
- `test_cli_task_commands.py`：requirement/task 创建、准备、阶段与文档命令。
- `test_cli_evidence_commands.py`：evidence、validation、handoff。
- `test_cli_task_context.py`：task context 的解析、能力矩阵和服务上下文。
- `test_cli_service_commands.py`：service 命令。
- `test_cli_material_commands.py`：material、discovery、intake。
- `test_cli_record_commands.py`：action、change、decision、suspicion。
- `test_cli_archive_commands.py`：archive 命令。

`tests/__init__.py` 用于保证共享测试模块使用稳定的包内导入。拆分只移动现有测试和必要的共享帮助函数，不改变断言语义。

### 索引模块

`codex_workbench.index` 保留现有公开 API：

- `IndexWriteResult`
- `IndexCheckResult`
- `generate_index_views`
- `check_generated_views`

内部职责拆为：

- `_index_types.py`：内部记录和快照数据结构。
- `_index_records.py`：扫描工作区、加载 YAML、组装快照。
- `_index_conflicts.py`：引用、ID、evidence 和 archive 冲突检测。
- `_index_views.py`：CURRENT、index、recovery 渲染及显示辅助函数。

公共入口负责调用这些组件、写入生成视图和比较 stale 状态。外部调用方继续只依赖 `codex_workbench.index`。

### 包与任务模块

`codex_workbench.packages` 保留现有公开函数和返回类型，作为兼容 facade。内部职责拆为：

- `_package_core.py`：返回类型、原子包写入、路径校验、加载与回滚等共享支撑。
- `_package_create.py`：requirement/task 创建和 requirement close。
- `_package_tasks.py`：task packet、stage、prepare、impact、review/implementation、blocked 和 obsolete 操作。

现有 CLI、materials、task context 和 validation 继续从 `codex_workbench.packages` 导入，不直接依赖私有模块。测试中针对实现细节的 monkeypatch 改为指向实际执行 I/O 的私有模块；公开行为断言保持不变。

## 结构约束

新增结构测试，表达本次拆分的维护目标：

- `index.py` 与 `packages.py` 必须保持为小型公共入口。
- `src/codex_workbench` 下单个 Python 模块不得重新增长到当前大文件量级。
- `test_cli*.py` 文件必须保持在可独立阅读的规模内。

约束阈值在实施计划中根据拆分后的自然边界确定，不能通过压缩格式或堆叠语句规避。

## 实施顺序

1. 新增会在当前结构上失败的结构约束测试，确认失败原因是文件规模。
2. 修正 registry 单元测试与仓库契约测试的分层。
3. 拆分 `test_cli.py`，运行全部 CLI 测试。
4. 拆分 `index.py`，运行 index、doctor、CLI 和集成测试。
5. 拆分 `packages.py`，运行 packages、validation、materials、task context、CLI 和集成测试。
6. 运行完整 pytest、Ruff、导入检查和 Git diff 检查。

每一步只做结构迁移；若测试暴露真实行为差异，暂停并单独调查，不在重构中混入行为修复。

## 验证策略

- 基线：完整测试套件在拆分前通过。
- 红灯：结构约束测试在拆分前因目标文件过大而失败。
- 分步绿灯：每完成一个领域拆分，运行直接相关测试。
- 最终绿灯：完整 `pytest` 与 Ruff 通过。
- 兼容性：验证现有公共导入仍可用，CLI help 和核心端到端流程保持通过。
- 差异复核：确认没有修改 generated views、状态 YAML、服务登记或用户现有工作文件。

## 风险与控制

- **循环导入**：私有模块依赖方向固定为 types/core → domain modules → public facade，禁止反向导入 facade。
- **monkeypatch 失效**：先识别测试接缝，再将 patch 目标调整到实际执行模块；不删除并发和回滚场景。
- **测试移动遗漏**：拆分前后比较 pytest 收集数量和测试名称集合。
- **输出细微变化**：依赖现有精确文本断言和端到端测试检测。
- **用户未提交工作被污染**：直接使用用户指定且状态干净的 `D:\Work\codex-workbench-main`，只修改本设计范围文件，提交时显式列出路径。

## 完成条件

- registry 单元测试不读取真实 registry，可变仓库资产只由明确的集成契约验证。
- `test_cli.py` 的职责已迁移到按命令域组织的测试文件。
- `index.py` 与 `packages.py` 成为兼容 facade，主要实现位于职责清晰的私有模块。
- 拆分前后 pytest 收集的测试集合一致，新增项仅为结构约束和仓库契约分层测试。
- 完整测试、Ruff 和差异检查通过。
