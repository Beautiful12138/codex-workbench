---
name: workbench-cli
description: Use when Codex 需要发现或使用 codex-workbench CLI 命令、写状态、生成/检查视图、确认参数、运行 doctor/index/archive，或不确定应该用哪个 python -m codex_workbench 命令。
---

# Workbench CLI

## 适用场景

使用本 skill 处理：

- 不确定 Workbench 有哪些 CLI 命令。
- 准备写入 requirement、task、evidence、service、archive 或其他状态。
- 需要用 `workspace context`、`task context`、`service context` 形成轻量工作面板。
- 需要生成或检查 `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md`。
- 需要运行 `doctor check`、`index check`、`archive preflight` 或其他只读检查。
- 需要确认命令参数、枚举或输出格式。

## 核心原则

CLI 是状态写入器和命令发现器，不是日常阅读负担。先判断用户要做什么，再用最小命令拿到现场；只有需要写状态、推进阶段、验证、关闭或归档时，才深入到具体命令。

写状态优先走 CLI，不手改 YAML 真源。Markdown 解释层可由 AI 填写，但生命周期状态、引用关系、generated views 和归档移动必须由 CLI 或对应工具维护。

默认路径：workspace context -> task context -> service context -> task package。`task context` 支持任务名称、ID 或 `task.yaml` 路径；对用户回复优先名称，ID 主要用于命令和消歧。`service context` 参数是服务名；如果用户只给路径，先匹配/登记服务或只读检查路径。

阶段推进、`task check` 或 `task set-stage` 前，先读 `workbench-gate-check` 做只读自检；本 skill 只负责命令发现和参数核对。

## 命令发现

从仓库根目录运行 CLI 时先设置当前源码路径：

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench <group> <command> --help
```

不知道命令在哪个组时，用：

```powershell
python -m codex_workbench --help
python -m codex_workbench task --help
```

不要为了发现命令默认扫描 `src/`。先读本 skill，再用 `--help` 核对当前 CLI。

## 日常动作表

| 想做的事 | 先用 | 再决定 |
| --- | --- | --- |
| 看当前能接什么 | `workspace context` | 是否需要选 task、看服务或只读回答 |
| 继续某个任务 | `task context` | 是否需要读 task 包、补 prepare、验证或门禁 |
| 看服务现场 | `service context` | 是否需要读服务目录、环境资料或扩大检查范围 |
| 纳入新需求 | `material add` / `discovery create` / `intake create` | 用户确认后再 `intake confirm` / `task create` |
| 准备实现 | `task prepare` | high/critical 优先带 `--reviewer subagent --review-independent`，再用 `task check --to in_progress` 预演 |
| 风险变化 | `task impact-set` | 再回到 `task context` 看缺口 |
| 记录验证 | `evidence create` / `validation apply` / `handoff set` | 再用 `task check --to done` 预演 |
| 刷新视图 | `index generate` / `index check` | generated views 只用于定位 |
| 健康检查 | `doctor check` | 只看硬问题，不让 doctor 代替判断 |
| 归档 | `archive preflight` / `archive version` | 必须已有关闭和归档授权 |

## 命令组速查

- `material`：材料登记，核心命令 `material add`。
- `discovery`：只读探索、观察、推断和待确认问题，核心命令 `discovery create`。
- `intake`：需求草案与用户确认，核心命令 `intake create`、`intake confirm`。
- `requirement`：需求关闭，核心命令 `requirement close`。
- `task`：任务创建、准备、风险画像、阶段门禁和任务说明，核心命令 `task create`、`task context`、`task prepare`、`task impact-set`、`task check`、`task set-stage`。
- `evidence` / `validation` / `handoff`：验证事实、验证判断和用户验收，核心命令 `evidence create`、`validation apply`、`handoff set`。
- `service` / `workspace`：工作区和服务上下文，核心命令 `workspace context`、`service context`；`service status` 主要用于调试和脚本。
- `action` / `change` / `decision` / `suspicion`：非任务记录和范围变化线索。
- `index` / `doctor`：生成视图和只读健康检查，核心命令 `index generate`、`index check`、`doctor check`。
- `archive`：归档预检、版本归档和历史查询，核心命令 `archive preflight`、`archive version`、`archive list`。

## 服务检查负载

`workspace context` 默认只读 registry 做轻量服务概览，不深扫服务路径、Git 或入口文件。需要真实服务现场时，优先点名 `service context <服务名>`；确实需要批量探测时才用 `workspace context --check-services`。

`task context` 对一个任务挂载的一批 `service_refs` 会去重，并默认只展开前 5 个唯一服务；剩余服务会保留名称和数量，并通过 `service_check_limited` 提醒。需要继续实现时，先用 `--service-check-limit` 扩大检查范围，或按需用 `service context <服务名>` 点名确认。

## 典型链路

小修、只读探索和普通讨论不默认走完整链路；只有需要纳入 Workbench、写状态、推进阶段、验证、关闭或归档时使用。

- 需求进入：`material add` -> `discovery create` -> `intake create` -> `intake confirm`。
- 任务开工：`task create` -> `task context` -> `task prepare` -> `task check --to in_progress` -> `task set-stage --stage in_progress`。
- 验证完成：`evidence create` -> `validation apply` -> `handoff set` -> `task check --to done` -> `task set-stage --stage done`。
- 归档：`requirement close` -> `archive preflight` -> `archive version`。
- 生成视图：`index generate` -> `index check`。

## 写状态边界

- requirement、task、evidence、validation、handoff、archive 状态必须走 CLI。
- `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md` 是生成视图，不能手改。
- task 创建后发现影响面变化，用 `task impact-set`，不要静默改 `risk_level`。
- 已有 `impact_profile` 时，`task prepare` / `task impact-set` 可局部覆盖字段；新建画像仍需 `--impact-action`。
- 进入阶段前用 `task check --to <stage>` 预演。
- 面对任务名称、服务名或“下一步做什么”时，优先用 `workspace context` / `task context` / `service context` 形成轻量工作面板，再决定是否需要更深阅读。
- `service status` 和 `task check` 是底层调试/门禁命令，不作为日常默认入口。
- `doctor check` 只查硬问题，不替代 evidence、验收或风险接受。

## 常见错误

- 直接手改 `task.yaml.stage`。
- 手工编辑 generated views。
- 用 action note 替代 task evidence。
- 不运行 `--help` 就猜参数。
- 不设置 `PYTHONPATH=src` 导致运行了其他 checkout 的包。
