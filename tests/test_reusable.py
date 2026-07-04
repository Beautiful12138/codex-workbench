from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from codex_workbench.cli import app


runner = CliRunner()


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )


def run_private_ledger(args: list[str], workspace_root: Path) -> subprocess.CompletedProcess[str]:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / ".codex" / "automations" / "reusable-materials" / "reusable_ledger.py"
    return subprocess.run(
        [sys.executable, str(script_path), *args, "--workspace-root", str(workspace_root)],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )


def test_reusable_memory_cli_reads_dimension_markdown(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    reusable_dir = tmp_path / "docs" / "reusable"
    reusable_dir.mkdir(parents=True)
    (reusable_dir / "workflow.md").write_text(
        "\n".join(
            [
                "# Workflow",
                "",
                "## 1. done 前确认 evidence",
                "正式 task 判断完成时，先确认 evidence 和 handoff。",
                "",
                "## 2. small-fix 保持边界清楚",
                "只在低风险、可验证、可回滚时使用 small-fix。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    listed = runner.invoke(app, ["reusable-memory", "list", "--workspace-root", str(tmp_path)])
    shown = runner.invoke(app, ["reusable-memory", "show", "workflow", "--workspace-root", str(tmp_path)])
    found = runner.invoke(app, ["reusable-memory", "find", "evidence", "--workspace-root", str(tmp_path)])
    fetched = runner.invoke(app, ["reusable-memory", "get", "workflow", "1", "--workspace-root", str(tmp_path)])

    assert listed.exit_code == 0
    assert "workflow: 2" in listed.output
    assert "services: 0" in listed.output
    assert shown.exit_code == 0
    assert "1. done 前确认 evidence" in shown.output
    assert "2. small-fix 保持边界清楚" in shown.output
    assert found.exit_code == 0
    assert "workflow 1. done 前确认 evidence" in found.output
    assert fetched.exit_code == 0
    assert fetched.output.startswith("## 1. done 前确认 evidence")
    assert "正式 task 判断完成时" in fetched.output


def test_reusable_ledger_is_not_exposed_to_daytime_cli() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "reusable-memory" in result.output
    assert "reusable-ledger" not in result.output


def test_private_reusable_ledger_records_monthly_run_and_change(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    init = run_private_ledger(["init", "--month", "2026-07"], tmp_path)
    add_run = run_private_ledger(
        [
            "add-run",
            "--month",
            "2026-07",
            "--run-date",
            "2026-07-04",
            "--result",
            "partial",
            "--summary",
            "nightly reusable maintenance",
        ],
        tmp_path,
    )
    add_count = run_private_ledger(
        [
            "add-dimension-count",
            "--month",
            "2026-07",
            "--run-id",
            "1",
            "--dimension",
            "workflow",
            "--count-before",
            "0",
            "--count-after",
            "1",
        ],
        tmp_path,
    )
    add_change = run_private_ledger(
        [
            "add-change",
            "--month",
            "2026-07",
            "--run-id",
            "1",
            "--action",
            "add",
            "--dimension",
            "workflow",
            "--memory-no-after",
            "1",
            "--title-after",
            "done 前确认 evidence",
            "--content-after",
            "## 1. done 前确认 evidence\n\n正式 task 判断完成时，先确认 evidence。",
            "--reason",
            "多个完成任务都需要同一条门禁记忆。",
            "--audit-sources-json",
            '["docs/archive/1.0.0/REQ-001"]',
        ],
        tmp_path,
    )
    update_run = run_private_ledger(
        [
            "update-run",
            "--month",
            "2026-07",
            "--run-id",
            "1",
            "--result",
            "completed",
            "--added-count",
            "1",
        ],
        tmp_path,
    )
    listed = run_private_ledger(["list-runs", "--month", "2026-07"], tmp_path)
    shown = run_private_ledger(["show-change", "1", "--month", "2026-07"], tmp_path)

    assert init.returncode == 0, init.stderr
    assert init.stdout.strip() == ".codex/automations/reusable-materials/ledger/2026-07.sqlite"
    assert add_run.returncode == 0, add_run.stderr
    assert add_run.stdout.strip() == "1"
    assert add_count.returncode == 0, add_count.stderr
    assert add_change.returncode == 0, add_change.stderr
    assert update_run.returncode == 0, update_run.stderr
    assert listed.returncode == 0, listed.stderr
    assert "1 2026-07-04 completed add=1 update=0 delete=0 merge=0" in listed.stdout
    assert shown.returncode == 0, shown.stderr
    assert "action: add" in shown.stdout
    assert "content_before:" not in shown.stdout
    assert "content_after: ## 1. done 前确认 evidence" in shown.stdout

    ledger_path = tmp_path / ".codex" / "automations" / "reusable-materials" / "ledger" / "2026-07.sqlite"
    with sqlite3.connect(ledger_path) as connection:
        change_count = connection.execute("SELECT COUNT(*) FROM memory_change").fetchone()[0]
    assert change_count == 1
