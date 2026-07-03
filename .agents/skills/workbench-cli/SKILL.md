---
name: workbench-cli
description: Use when Codex 需要发现或使用 codex-workbench CLI 命令、写状态、生成/检查视图、确认参数、运行 doctor/index/archive，或不确定应该用哪个 python -m codex_workbench 命令。
---

# Workbench CLI

## 适用场景

使用本 skill 处理：

- 不确定 Workbench 有哪些 CLI 命令。
- 需要写入 requirement、task、evidence、action、change、decision、suspicion、service 或 archive 状态。
- 需要用 `workspace context` 查看不落盘的当前驾驶舱。
- 需要用 `task context` 或 `service context` 快速判断当前任务/服务是否可接、缺什么。
- 需要生成或检查 `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md`。
- 需要运行 `doctor check`、`index check`、`archive preflight` 或其他只读检查。
- 需要确认某个命令参数、枚举或输出格式。

## 核心原则

写状态优先走 CLI，不手改 YAML 真源。Markdown 解释层可由 AI 填写，但生命周期状态、引用关系、generated views 和归档移动必须由 CLI 或对应工具维护。

默认路径：workspace context -> task context -> service context -> task package。`task context` 支持任务名称、ID 或 `task.yaml` 路径；对用户回复优先名称，ID 主要用于命令和消歧。`service context` 参数是服务名；如果用户只给路径，先匹配/登记服务或只读检查路径。

阶段推进、`task check` 或 `task set-stage` 前，先读 `workbench-gate-check` 做只读自检；本 skill 只负责命令发现和参数核对。

执行命令前，如果参数不确定，先运行：

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench <group> <command> --help
```

在本仓库测试或运行 CLI 时设置 `PYTHONPATH=src`，避免其他 checkout 的包遮蔽当前源码。

## 命令发现

从仓库根目录使用：

```powershell
$env:PYTHONPATH='src'
python -m codex_workbench --help
python -m codex_workbench task --help
python -m codex_workbench task create --help
```

不要为了发现命令默认扫描 `src/`。先读本 skill，再用 `--help` 核对当前 CLI。

## 命令组

- `material`：材料登记。
- `workspace`：根目录发现和不落盘驾驶舱。
- `discovery`：只读探索、观察、推断、假设和待确认问题。
- `intake`：需求草案创建和用户确认。
- `requirement`：需求关闭。
- `task`：任务创建、准备、风险画像、阶段门禁和任务内说明文档。
- `evidence`：验证事实。
- `validation`：把 evidence 判断写回 task。
- `handoff`：用户验收交接。
- `service`：服务登记和只读状态。
- `action`：非任务动作记录。
- `change`：范围变化分类和记录。
- `decision`：长期决策记录。
- `suspicion`：疑点线索记录。
- `index`：生成或检查 `CURRENT.md`、`docs/generated/index.md`、`docs/generated/recovery.md`。
- `doctor`：只读健康检查。
- `archive`：归档预检、版本归档和历史查询。

## 热路径命令

```powershell
$env:PYTHONPATH='src'

python -m codex_workbench workspace context --workspace-root .
python -m codex_workbench task context ...
python -m codex_workbench task context ... --service-check-limit 10
python -m codex_workbench service context ...

# 需要写状态、推进阶段、验证或归档时，再查对应命令 help。
python -m codex_workbench <group> <command> --help
```

## 按需命令

```powershell
python -m codex_workbench material add ...
python -m codex_workbench discovery create ...
python -m codex_workbench intake create ...
python -m codex_workbench intake confirm ...
python -m codex_workbench requirement close ...

python -m codex_workbench task create ...
python -m codex_workbench task prepare ...
python -m codex_workbench task impact-set ...
python -m codex_workbench task check ...
python -m codex_workbench task set-stage ...
python -m codex_workbench task block ...
python -m codex_workbench task obsolete ...
python -m codex_workbench task review-create ...
python -m codex_workbench task implementation-create ...

python -m codex_workbench evidence create ...
python -m codex_workbench validation apply ...
python -m codex_workbench handoff set ...

python -m codex_workbench service add ...
python -m codex_workbench service list
python -m codex_workbench workspace context --check-services --workspace-root .  # 显式批量探测概览展示服务
python -m codex_workbench service status ...  # 调试/脚本用

python -m codex_workbench action create ...
python -m codex_workbench change classify ...
python -m codex_workbench change create ...
python -m codex_workbench decision create ...
python -m codex_workbench suspicion create ...

python -m codex_workbench index generate --workspace-root .
python -m codex_workbench index check --workspace-root .
python -m codex_workbench doctor check --workspace-root .

python -m codex_workbench archive preflight ...
python -m codex_workbench archive version ...
python -m codex_workbench archive list
```

`workspace context` 默认只读 registry 做轻量服务概览，不深扫服务路径、Git 或入口文件。需要真实服务现场时，优先点名 `service context <服务名>`；确实需要批量探测时才用 `workspace context --check-services`。

`task context` 对一个任务挂载的一批 `service_refs` 会去重，并默认只展开前 5 个唯一服务；剩余服务会保留名称和数量，并通过 `service_check_limited` 提醒。需要继续实现时，先用 `--service-check-limit` 扩大检查范围，或按需用 `service context <服务名>` 点名确认。

## 正式任务典型链路

小修、只读探索和普通讨论不默认走这些链路；只有需要纳入 Workbench、写状态、推进阶段、验证、关闭或归档时使用。

需求进入：

```text
material add
-> discovery create
-> intake create
-> intake confirm
```

任务开工：

```text
task create
-> task context
-> task prepare
-> task context
-> task check --to in_progress
-> task set-stage --stage in_progress
```

风险变化：

```text
task impact-set --reason "..."
-> task check --to in_progress
```

验证完成：

```text
evidence create
-> validation apply
-> handoff set
-> task check --to done
-> task set-stage --stage done
```

归档：

```text
requirement close
-> archive preflight
-> archive version
```

生成视图：

```text
index generate
-> index check
```

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
