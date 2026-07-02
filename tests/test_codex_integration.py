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
        "# CURRENT\n\nrole: 入口卡\nworkspace_status: baseline\n",
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

    assert "CURRENT.md" in session_text
    assert "CLI" in session_text
    assert "讨论" in prompt_text
    assert "只读探索" in prompt_text
    assert "不写状态" in prompt_text
    assert len(session_text.splitlines()) <= 4
    assert len(prompt_text.splitlines()) <= 4
    assert len(session_text) < 420
    assert len(prompt_text) < 420


def test_workbench_skills_are_concise_codex_skills() -> None:
    expected = {
        "workbench-resume",
        "workbench-task",
        "workbench-evidence",
        "workbench-archive",
    }

    for name in expected:
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
        assert len(body.splitlines()) < 90
        assert "## When to Use" not in body
        assert "README.md" not in body
        assert "CHANGELOG" not in body
        assert "codex-workbench-philosophy" not in body


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
            "REQ-DOGFOOD",
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
            "REQ-DOGFOOD",
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
            "TASK-DOGFOOD",
            "--requirement-id",
            "REQ-DOGFOOD",
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

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-DOGFOOD" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert requirement["task_refs"] == ["TASK-DOGFOOD"]

    invoke_ok(
        [
            "evidence",
            "create",
            "EV-TASK-DOGFOOD",
            "--task-id",
            "TASK-DOGFOOD",
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
            "TASK-DOGFOOD",
            "--evidence-id",
            "EV-TASK-DOGFOOD",
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
            "TASK-DOGFOOD",
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
            "TASK-DOGFOOD",
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
            "REQ-DOGFOOD",
            "--authorization-note",
            "用户确认可以归档样例版本。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            root,
        ],
    )
    assert missing_closure.exit_code != 0
    assert "missing_requirement_closure: REQ-DOGFOOD" in combined_output(missing_closure)

    invoke_ok(
        [
            "requirement",
            "close",
            "REQ-DOGFOOD",
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
            "REQ-DOGFOOD",
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
            "REQ-DOGFOOD",
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
    assert not (tmp_path / "docs" / "active" / "REQ-DOGFOOD").exists()
    assert not (tmp_path / "docs" / "active" / "TASK-DOGFOOD").exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-dogfood" / "REQ-DOGFOOD").exists()
    assert (tmp_path / "docs" / "archive" / "0.1.0-dogfood" / "TASK-DOGFOOD").exists()
