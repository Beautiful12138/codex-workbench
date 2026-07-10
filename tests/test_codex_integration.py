from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from codex_workbench.cli import app
from codex_workbench.models import ServiceRegistry


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


def test_repository_service_registry_matches_current_schema() -> None:
    registry_path = PROJECT_ROOT / "services" / "registry.yaml"
    registry_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    registry = ServiceRegistry.model_validate(registry_data)

    assert registry.schema_version == "0.1"


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

    assert len(session_text.splitlines()) <= 4
    assert len(prompt_text.splitlines()) <= 4
    assert len(session_text) < 512
    assert len(prompt_text) < 512


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
