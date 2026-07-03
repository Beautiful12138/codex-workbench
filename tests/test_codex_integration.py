from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from codex_workbench.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text(
        "# CURRENT\n\nrole: 最近工作面板\nworkspace_status: baseline\n",
        encoding="utf-8",
    )
    (root / "services" / "registry.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "0.1", "services": []},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def combined_output(result) -> str:
    return result.output + getattr(result, "stderr", "")


def invoke_ok(args: list[str]) -> str:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, combined_output(result)
    return result.output


def output_value(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    raise AssertionError(f"missing output line: {prefix}\n{output}")


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_hook(script_name: str, workspace_root: Path, payload: dict[str, object]) -> dict:
    script = PROJECT_ROOT / ".codex" / "hooks" / script_name
    assert script.exists()
    before = snapshot_files(workspace_root)
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=workspace_root,
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    after = snapshot_files(workspace_root)

    assert completed.returncode == 0, completed.stderr
    assert after == before
    return json.loads(completed.stdout)


def hook_context_text(output: dict) -> str:
    hook_output = output["hookSpecificOutput"]
    text = hook_output["additionalContext"]
    assert isinstance(text, str)
    return text


def test_hooks_json_and_scripts_are_short_read_only_reminders(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    hooks_config = PROJECT_ROOT / ".codex" / "hooks.json"

    config = json.loads(hooks_config.read_text(encoding="utf-8"))
    commands = json.dumps(config, ensure_ascii=False)
    assert "SessionStart" in config["hooks"]
    assert "UserPromptSubmit" in config["hooks"]
    assert "doctor" not in commands.lower()
    assert "archive" not in commands.lower()

    session_text = hook_context_text(
        run_hook("session_start.py", tmp_path, {"hook_event_name": "SessionStart"})
    )
    prompt_text = hook_context_text(
        run_hook(
            "user_prompt_submit.py",
            tmp_path,
            {
                "hook_event_name": "UserPromptSubmit",
                "user_prompt": "我们讨论一下是否需要新字段。",
            },
        )
    )

    assert "workspace context" in session_text
    assert "CURRENT/recovery/index 只辅助定位" in session_text
    assert "CLI" in session_text
    assert "讨论" in prompt_text
    assert "只读探索" in prompt_text
    assert "先校验再配合" in prompt_text
    assert "多思考一步" in prompt_text
    assert "不写状态" in prompt_text
    assert len(session_text.splitlines()) <= 4
    assert len(prompt_text.splitlines()) <= 4
    assert len(session_text) < 420
    assert len(prompt_text) < 420


def test_runtime_guidance_covers_multi_package_workbench_contract() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    current_text = (PROJECT_ROOT / "CURRENT.md").read_text(encoding="utf-8")
    workspace_text = (PROJECT_ROOT / "WORKSPACE.md").read_text(encoding="utf-8")
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    recovery_policy = PROJECT_ROOT / "docs" / "policies" / "recovery-and-concurrency.md"

    assert "多个需求、多个任务、多个服务" in agents_text
    assert "工作对象选择" in agents_text
    assert "显式路径" in agents_text
    assert "不作为单任务锁" in current_text
    assert "并发工作单元" in workspace_text
    assert recovery_policy.exists()
    policy_text = recovery_policy.read_text(encoding="utf-8")
    assert "显式路径优先" in policy_text
    assert "generated views" in policy_text
    assert "无法唯一判断" in policy_text
    for text in (agents_text, resume_skill, policy_text):
        assert "名称优先" in text
        assert "ID 是内部锚点" in text
        assert "默认不向用户暴露" in text


def test_runtime_guidance_discovers_environment_markdown_directory() -> None:
    environment_dir = PROJECT_ROOT / "environments"
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    workspace_text = (PROJECT_ROOT / "WORKSPACE.md").read_text(encoding="utf-8")
    environment_policy = (
        PROJECT_ROOT / "docs" / "policies" / "services-and-environment.md"
    ).read_text(encoding="utf-8")
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    task_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-task" / "SKILL.md"
    ).read_text(encoding="utf-8")
    environment_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-environment" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert environment_dir.exists()
    assert (environment_dir / ".gitkeep").exists()
    assert "environments/" in agents_text
    assert "workbench-environment" in agents_text
    assert "environments/" in readme_text
    assert "自由 Markdown" in workspace_text
    assert "不由 CLI" in environment_policy
    assert "固定结构" not in environment_policy
    assert "environments/" in resume_skill
    assert "environments/" in task_skill
    assert "GitLab" in environment_skill
    assert "账号密码" in environment_skill
    assert "服务器" in environment_skill
    assert "数据库" in environment_skill


def test_agents_md_is_a_short_routing_card() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lines = agents_text.splitlines()

    assert len(lines) <= 115
    assert "## 协作判断" in agents_text
    assert "先校验再配合" in agents_text
    assert "多思考一步" in agents_text
    assert "## 必读触发器" in agents_text
    assert "## 按场景读取" in agents_text
    assert "workbench-resume" in agents_text
    assert "workbench-cli" in agents_text
    assert "workbench-task" in agents_text
    assert "workbench-environment" in agents_text
    assert "workbench-gate-check" in agents_text
    assert "workbench-evidence" in agents_text
    assert "workbench-archive" in agents_text
    assert "## 风险入口" not in agents_text
    assert "## 读取深度" not in agents_text


def test_runtime_guidance_routes_empty_baseline_and_self_maintenance() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workspace_text = (PROJECT_ROOT / "WORKSPACE.md").read_text(encoding="utf-8")
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    action_policy = (
        PROJECT_ROOT / "docs" / "policies" / "action-routing.md"
    ).read_text(encoding="utf-8")
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    task_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-task" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "空工作台" in agents_text
    assert "baseline" in agents_text
    assert "codex-workbench 自身" in agents_text
    assert "maintenance_action" in agents_text
    assert "只要要写状态、推进阶段、生成视图、检查状态、归档" in agents_text

    assert "baseline，且没有 active requirement/task" in resume_skill
    assert "用户问下一步" in resume_skill
    assert "2-3 个可选入口" in resume_skill
    assert "不主动创建任务" in resume_skill
    assert "先检查是否需要 `workbench-cli`" in resume_skill
    assert "codex-workbench 自身" in resume_skill

    assert "Workbench 自身维护" in action_policy
    assert "不强制创建 requirement/task" in action_policy
    assert "maintenance_action / repo maintenance" in action_policy
    assert "codex-workbench 自身" in task_skill

    expected_roles = [
        "AGENTS.md：AI 启动路由器",
        "CURRENT.md：最近工作面板",
        "README.md：人类使用说明",
        "WORKSPACE.md：目录地图",
        "skills：按场景的详细操作手册",
        "policies：规则边界",
        "hooks：轻提醒，不决策",
    ]
    for role in expected_roles:
        assert role in workspace_text or role in readme_text


def test_runtime_guidance_prefers_workspace_context_before_deeper_reads() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    cli_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-cli" / "SKILL.md"
    ).read_text(encoding="utf-8")
    task_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-task" / "SKILL.md"
    ).read_text(encoding="utf-8")
    gate_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-gate-check" / "SKILL.md"
    ).read_text(encoding="utf-8")

    default_path = "workspace context -> task context -> service context -> task package"
    for text in (agents_text, readme_text, resume_skill, cli_skill):
        assert default_path in text
    assert "$env:PYTHONPATH='src'" in agents_text
    assert "python -m codex_workbench workspace context --workspace-root ." in agents_text
    assert "service status" in cli_skill
    assert "调试" in cli_skill
    assert "task check" in gate_skill
    assert "底层门禁命令" in gate_skill
    assert "工作面板：选择到 task 或创建 task 后，用 `task context" in task_skill


def test_runtime_guidance_treats_waiting_feedback_as_normal_resume_state() -> None:
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    recovery_policy = (
        PROJECT_ROOT / "docs" / "policies" / "recovery-and-concurrency.md"
    ).read_text(encoding="utf-8")

    for text in (resume_skill, recovery_policy):
        assert "等待反馈" in text
        assert "不是阻塞" in text
        assert "waiting_user_validation" in text
        assert "verification_pending" in text


def test_runtime_guidance_routes_small_fix_through_risk_formula() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    action_policy = (
        PROJECT_ROOT / "docs" / "policies" / "action-routing.md"
    ).read_text(encoding="utf-8")
    resume_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-resume" / "SKILL.md"
    ).read_text(encoding="utf-8")
    task_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-task" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "small-fix" in agents_text
    assert "小型低风险修改" in agents_text
    assert "风险公式" in agents_text

    assert "`small-fix`" in action_policy
    assert "影响面画像" in action_policy
    assert "risk-and-process.md" in action_policy
    assert "environment" in action_policy
    assert "data_effect" in action_policy
    assert "external_effect" in action_policy
    assert "blast_radius" in action_policy
    assert "reversibility" in action_policy
    assert "contract_change" in action_policy
    assert "security_or_permission" in action_policy
    assert "verification_confidence" in action_policy
    assert "正式 task 或 ops_action" in action_policy

    assert "小型低风险修改" in resume_skill
    assert "风险公式" in resume_skill
    assert "最小改动和最小验证" in resume_skill
    assert "不自动创建正式 task" in task_skill
    assert "不能用 small-fix 绕过风险公式" in task_skill


def test_runtime_guidance_covers_test_environment_and_partial_impact_updates() -> None:
    risk_policy = (PROJECT_ROOT / "docs" / "policies" / "risk-and-process.md").read_text(
        encoding="utf-8"
    )
    model_policy = (PROJECT_ROOT / "docs" / "policies" / "model-schema.md").read_text(
        encoding="utf-8"
    )
    task_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-task" / "SKILL.md"
    ).read_text(encoding="utf-8")
    cli_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-cli" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for text in (risk_policy, model_policy):
        assert "local | test | sandbox | personal | shared | production | unknown" in text
    assert "local、test、sandbox、personal、shared、production" in task_skill
    for text in (risk_policy, task_skill, cli_skill):
        assert "局部覆盖" in text
        assert "新建画像仍" in text


def test_runtime_guidance_discovers_gate_check_skill() -> None:
    agents_text = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    cli_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-cli" / "SKILL.md"
    ).read_text(encoding="utf-8")
    gate_skill_path = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-gate-check" / "SKILL.md"
    )

    assert "阶段推进前、task check、set-stage、in_progress、done、blocked、obsolete" in agents_text
    assert gate_skill_path.exists()
    gate_skill = gate_skill_path.read_text(encoding="utf-8")
    assert "name: workbench-gate-check" in gate_skill
    assert "Use when" in gate_skill
    assert "codex-workbench" in gate_skill
    assert "只读自检" in gate_skill
    assert "不写状态" in gate_skill
    assert "task check --to" in gate_skill
    assert "implementation-ready" in gate_skill
    assert "impact_profile" in gate_skill
    assert "evidence" in gate_skill
    assert "validation" in gate_skill
    assert "handoff" in gate_skill
    assert "暂停确认" in gate_skill
    assert "workbench-gate-check" in cli_skill


def test_gate_check_output_is_not_delivery_evidence() -> None:
    gate_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-gate-check" / "SKILL.md"
    ).read_text(encoding="utf-8")
    evidence_skill = (
        PROJECT_ROOT / ".agents" / "skills" / "workbench-evidence" / "SKILL.md"
    ).read_text(encoding="utf-8")
    state_policy = (PROJECT_ROOT / "docs" / "policies" / "state-and-gates.md").read_text(
        encoding="utf-8"
    )

    for text in (gate_skill, evidence_skill, state_policy):
        assert "gate-check 结果不能作为交付 evidence" in text
        assert "不能替代任务本身的交付验证事实" in text


def test_runtime_baseline_does_not_include_construction_notes() -> None:
    baseline_paths = [
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "WORKSPACE.md",
        *sorted((PROJECT_ROOT / "docs" / "policies").glob("*.md")),
        *sorted((PROJECT_ROOT / ".agents" / "skills").glob("workbench-*/SKILL.md")),
        *sorted((PROJECT_ROOT / "templates" / "work-products").glob("*.md")),
    ]
    forbidden_phrases = [
        "最终目标",
        "建设期",
        "后续增强",
        "只是一个架子",
        "保持短",
        "改造计划",
        "codex-workbench-final-target",
        "engineering-harness",
        "Harness",
        "remodel",
    ]

    offenders: list[str] = []
    for path in baseline_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            if phrase in text:
                relative = path.relative_to(PROJECT_ROOT).as_posix()
                offenders.append(f"{relative}: {phrase}")

    assert offenders == []


def test_workbench_skills_are_runtime_procedures() -> None:
    required = {
        "workbench-resume": [
            "适用场景",
            "读取顺序",
            "工作对象选择",
            "停止点",
            "多个 active task",
        ],
        "workbench-cli": [
            "适用场景",
            "命令发现",
            "典型链路",
            "写状态",
            "python -m codex_workbench",
        ],
        "workbench-task": [
            "适用场景",
            "material",
            "discovery",
            "intake",
            "task prepare",
            "阶段推进",
        ],
        "workbench-evidence": [
            "适用场景",
            "evidence create",
            "validation apply",
            "handoff set",
            "不能算 evidence",
        ],
        "workbench-environment": [
            "适用场景",
            "environments/",
            "读取顺序",
            "自动发现线索",
            "输出边界",
        ],
        "workbench-gate-check": [
            "适用场景",
            "只读自检",
            "task check",
            "implementation-ready",
            "暂停确认",
        ],
        "workbench-archive": [
            "适用场景",
            "requirement close",
            "archive preflight",
            "archive version",
            "冷历史",
        ],
    }

    for name, required_phrases in required.items():
        skill_path = PROJECT_ROOT / ".agents" / "skills" / name / "SKILL.md"
        assert skill_path.exists()
        text = skill_path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        assert len(parts) == 3
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()

        assert set(frontmatter) == {"name", "description"}
        assert frontmatter["name"] == name
        assert frontmatter["description"].startswith("Use when")
        assert "codex-workbench" in frontmatter["description"]
        assert len(frontmatter["description"]) < 280
        assert len(body.splitlines()) <= 220
        for phrase in required_phrases:
            assert phrase in body
        assert "最终目标" not in body
        assert "建设期" not in body
        assert "codex-workbench-final-target" not in body


def test_workbench_cli_skill_lists_core_commands() -> None:
    skill_path = PROJECT_ROOT / ".agents" / "skills" / "workbench-cli" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")

    required_commands = [
        "material add",
        "workspace context",
        "discovery create",
        "intake create",
        "intake confirm",
        "task create",
        "task context",
        "task prepare",
        "task impact-set",
        "task check",
        "task set-stage",
        "service context",
        "evidence create",
        "validation apply",
        "handoff set",
        "index generate",
        "index check",
        "doctor check",
        "archive preflight",
        "archive version",
    ]

    for command in required_commands:
        assert command in text
    assert "--help" in text
    assert "PYTHONPATH" in text
    assert "CURRENT.md" in text
    assert "docs/generated/recovery.md" in text


def test_dogfood_cli_runs_material_to_handoff_close_and_archive(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    root = str(tmp_path)

    invoke_ok(
        [
            "material",
            "add",
            "MAT-DOGFOOD",
            "--title",
            "样例需求材料",
            "--source",
            "user-chat",
            "--summary",
            "用户希望验证 Workbench 能跑通一条轻量闭环。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "discovery",
            "create",
            "DISC-DOGFOOD",
            "--title",
            "样例发现",
            "--material-ref",
            "MAT-DOGFOOD",
            "--confirmed-fact",
            "这是本地个人工作区样例。",
            "--observation",
            "普通讨论不应写状态。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )
    invoke_ok(
        [
            "intake",
            "create",
            "REQ-20260702-900",
            "--title",
            "验证 Workbench 闭环",
            "--goal",
            "跑通材料到归档的最小闭环。",
            "--acceptance",
            "任务完成前有 evidence 和 handoff。",
            "--material-ref",
            "MAT-DOGFOOD",
            "--discovery-ref",
            "DISC-DOGFOOD",
            "--confirmed-fact",
            "用户确认这是样例需求。",
            "--non-goal",
            "不接管外部服务 Git。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )
    invoke_ok(
        [
            "intake",
            "confirm",
            "REQ-20260702-900",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )
    invoke_ok(
        [
            "service",
            "add",
            "codex-workbench",
            "--path",
            root,
            "--purpose",
            "样例需求关联的本地工具仓库。",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "task",
            "create",
            "REQ-20260702-900-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-900",
            "--title",
            "验证闭环",
            "--user-goal",
            "证明 Workbench 任务可以验证、交接并归档。",
            "--done",
            "evidence 记录通过。",
            "--done",
            "handoff 被用户接受。",
            "--next",
            "记录验证事实。",
            "--service-ref",
            "codex-workbench",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-900" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert requirement["task_refs"] == ["REQ-20260702-900-TASK-20260702-001"]

    invoke_ok(
        [
            "evidence",
            "create",
            "EV-REQ-20260702-900-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-900-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "dogfood 样例命令按预期执行。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )
    invoke_ok(
        [
            "validation",
            "apply",
            "REQ-20260702-900-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-900-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "handoff",
            "set",
            "REQ-20260702-900-TASK-20260702-001",
            "--status",
            "accepted",
            "--note",
            "用户确认样例闭环可接受。",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "task",
            "set-stage",
            "REQ-20260702-900-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            root,
        ]
    )

    missing_closure = runner.invoke(
        app,
        [
            "archive",
            "preflight",
            "0.1.0-dogfood",
            "--requirement-id",
            "REQ-20260702-900",
            "--authorization-note",
            "用户确认可以归档样例版本。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            root,
        ],
    )
    assert missing_closure.exit_code != 0
    assert "missing_requirement_closure: REQ-20260702-900" in combined_output(missing_closure)

    invoke_ok(
        [
            "requirement",
            "close",
            "REQ-20260702-900",
            "--note",
            "用户确认需求已关闭。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-01",
        ]
    )
    closed_requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert closed_requirement["confirmations"] == [
        {
            "type": "requirement_closure",
            "source": "user",
            "note": "用户确认需求已关闭。",
        }
    ]

    preflight_output = invoke_ok(
        [
            "archive",
            "preflight",
            "0.1.0-dogfood",
            "--requirement-id",
            "REQ-20260702-900",
            "--authorization-note",
            "用户确认可以归档样例版本。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            root,
        ]
    )
    archive_output = invoke_ok(
        [
            "archive",
            "version",
            "0.1.0-dogfood",
            "--requirement-id",
            "REQ-20260702-900",
            "--authorization-note",
            "用户确认可以归档样例版本。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            root,
        ]
    )

    assert "archive preflight clean" in preflight_output
    assert "archived docs/archive/0.1.0-dogfood/archive.yaml" in archive_output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-900").exists()
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-900-TASK-20260702-001").exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-dogfood" / "REQ-20260702-900").exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-dogfood" / "REQ-20260702-900-TASK-20260702-001").exists()


def test_dogfood_cli_runs_auto_id_material_to_archive(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    root = str(tmp_path)
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T09:00:00+08:00",
    )

    invoke_ok(
        [
            "material",
            "add",
            "MAT-AUTO",
            "--title",
            "自动编号样例材料",
            "--source",
            "user-chat",
            "--summary",
            "用户希望验证 Workbench 自动编号闭环。",
            "--received-at",
            "2026-07-02",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "discovery",
            "create",
            "DISC-AUTO",
            "--title",
            "自动编号样例发现",
            "--material-ref",
            "MAT-AUTO",
            "--confirmed-fact",
            "这是自动编号 dogfood。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-02",
        ]
    )
    intake_output = invoke_ok(
        [
            "intake",
            "create",
            "--title",
            "验证自动编号闭环",
            "--goal",
            "不手写需求和任务 ID 也能跑通闭环。",
            "--acceptance",
            "任务完成前有 evidence 和 handoff。",
            "--material-ref",
            "MAT-AUTO",
            "--discovery-ref",
            "DISC-AUTO",
            "--workspace-root",
            root,
        ]
    )
    requirement_id = output_value(intake_output, "created requirement_id=")

    invoke_ok(["intake", "confirm", requirement_id, "--workspace-root", root])
    invoke_ok(
        [
            "service",
            "add",
            "codex-workbench",
            "--path",
            root,
            "--purpose",
            "自动编号样例关联的本地工具仓库。",
            "--workspace-root",
            root,
        ]
    )
    task_output = invoke_ok(
        [
            "task",
            "create",
            "--requirement-id",
            requirement_id,
            "--title",
            "验证自动编号任务",
            "--user-goal",
            "证明自动生成 task ID 后 AI 可以继续闭环。",
            "--done",
            "evidence 记录通过。",
            "--done",
            "handoff 被用户接受。",
            "--next",
            "记录验证事实。",
            "--service-ref",
            "codex-workbench",
            "--workspace-root",
            root,
        ]
    )
    task_id = output_value(task_output, "created task_id=")
    evidence_id = f"EV-{task_id}"

    assert requirement_id == "REQ-20260702-001"
    assert task_id == "REQ-20260702-001-TASK-20260702-001"
    current_text = (tmp_path / "CURRENT.md").read_text(encoding="utf-8")
    recovery_text = (tmp_path / "docs" / "generated" / "recovery.md").read_text(
        encoding="utf-8"
    )
    assert task_id in current_text
    assert task_id in recovery_text

    invoke_ok(
        [
            "task",
            "prepare",
            task_id,
            "--working-scope",
            "只验证自动编号闭环。",
            "--risk-trigger",
            "需要修改外部服务仓库时暂停。",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(["task", "set-stage", task_id, "--stage", "in_progress", "--workspace-root", root])
    invoke_ok(
        [
            "evidence",
            "create",
            evidence_id,
            "--task-id",
            task_id,
            "--conclusion",
            "passed",
            "--key-output",
            "自动编号 dogfood 样例命令按预期执行。",
            "--workspace-root",
            root,
            "--updated-at",
            "2026-07-02",
        ]
    )
    invoke_ok(
        [
            "validation",
            "apply",
            task_id,
            "--evidence-id",
            evidence_id,
            "--status",
            "passed",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(
        [
            "handoff",
            "set",
            task_id,
            "--status",
            "accepted",
            "--note",
            "用户确认自动编号闭环可接受。",
            "--workspace-root",
            root,
        ]
    )
    invoke_ok(["task", "set-stage", task_id, "--stage", "done", "--workspace-root", root])
    invoke_ok(
        [
            "requirement",
            "close",
            requirement_id,
            "--note",
            "用户确认需求已关闭。",
            "--workspace-root",
            root,
        ]
    )
    preflight_output = invoke_ok(
        [
            "archive",
            "preflight",
            "0.1.0-auto-dogfood",
            "--requirement-id",
            requirement_id,
            "--authorization-note",
            "用户确认可以归档自动编号样例版本。",
            "--archived-at",
            "2026-07-02",
            "--workspace-root",
            root,
        ]
    )
    archive_output = invoke_ok(
        [
            "archive",
            "version",
            "0.1.0-auto-dogfood",
            "--requirement-id",
            requirement_id,
            "--authorization-note",
            "用户确认可以归档自动编号样例版本。",
            "--archived-at",
            "2026-07-02",
            "--workspace-root",
            root,
        ]
    )

    assert "archive preflight clean" in preflight_output
    assert "archived docs/archive/0.1.0-auto-dogfood/archive.yaml" in archive_output
    assert not (tmp_path / "docs" / "active" / requirement_id).exists()
    assert not (tmp_path / "docs" / "active" / task_id).exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-auto-dogfood" / requirement_id).exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-auto-dogfood" / task_id).exists()
