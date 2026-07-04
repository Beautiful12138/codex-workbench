from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .io import read_text_utf8

LEDGER_DIR = Path(".codex") / "automations" / "reusable-materials" / "ledger"


@dataclass(frozen=True)
class LedgerPaths:
    month: str
    path: Path


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def ledger_paths(workspace_root: Path, month: str | None = None) -> LedgerPaths:
    selected_month = month or current_month()
    return LedgerPaths(
        month=selected_month,
        path=workspace_root / LEDGER_DIR / f"{selected_month}.sqlite",
    )


def init_ledger(workspace_root: Path, month: str | None = None) -> LedgerPaths:
    paths = ledger_paths(workspace_root, month)
    paths.path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(paths.path) as connection:
        _init_schema(connection)
    return paths


def add_run(
    workspace_root: Path,
    *,
    month: str | None = None,
    run_date: str | None = None,
    started_at: str | None = None,
    result: str = "partial",
    summary: str | None = None,
) -> int:
    paths = init_ledger(workspace_root, month)
    now = _now_iso()
    with sqlite3.connect(paths.path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO nightly_run (
              run_date, started_at, result, summary
            )
            VALUES (?, ?, ?, ?)
            """,
            (run_date or date.today().isoformat(), started_at or now, result, summary),
        )
        return int(cursor.lastrowid)


def update_run(
    workspace_root: Path,
    *,
    run_id: int,
    month: str | None = None,
    finished_at: str | None = None,
    result: str | None = None,
    summary: str | None = None,
    added_count: int | None = None,
    updated_count: int | None = None,
    deleted_count: int | None = None,
    merged_count: int | None = None,
) -> None:
    paths = init_ledger(workspace_root, month)
    assignments: list[str] = []
    values: list[object] = []
    for column, value in (
        ("finished_at", finished_at),
        ("result", result),
        ("summary", summary),
        ("added_count", added_count),
        ("updated_count", updated_count),
        ("deleted_count", deleted_count),
        ("merged_count", merged_count),
    ):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    if not assignments:
        return
    values.append(run_id)
    with sqlite3.connect(paths.path) as connection:
        connection.execute(
            f"UPDATE nightly_run SET {', '.join(assignments)} WHERE id = ?",
            values,
        )


def add_dimension_count(
    workspace_root: Path,
    *,
    run_id: int,
    dimension: str,
    count_before: int | None = None,
    count_after: int | None = None,
    month: str | None = None,
) -> int:
    paths = init_ledger(workspace_root, month)
    with sqlite3.connect(paths.path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO dimension_count (
              run_id, dimension, count_before, count_after
            )
            VALUES (?, ?, ?, ?)
            """,
            (run_id, dimension, count_before, count_after),
        )
        return int(cursor.lastrowid)


def add_change(
    workspace_root: Path,
    *,
    run_id: int,
    action: str,
    dimension: str,
    memory_no_before: int | None = None,
    memory_no_after: int | None = None,
    title_before: str | None = None,
    title_after: str | None = None,
    content_before: str | None = None,
    content_after: str | None = None,
    content_before_file: Path | None = None,
    content_after_file: Path | None = None,
    reason: str | None = None,
    related_items_json: str | None = None,
    audit_sources: str | None = None,
    month: str | None = None,
) -> int:
    paths = init_ledger(workspace_root, month)
    before = read_text_utf8(content_before_file) if content_before_file else content_before
    after = read_text_utf8(content_after_file) if content_after_file else content_after
    with sqlite3.connect(paths.path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO memory_change (
              run_id, action, dimension, memory_no_before, memory_no_after,
              title_before, title_after, content_before, content_after,
              reason, related_items_json, audit_sources, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                action,
                dimension,
                memory_no_before,
                memory_no_after,
                title_before,
                title_after,
                before,
                after,
                reason,
                related_items_json,
                audit_sources,
                _now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def list_runs(workspace_root: Path, *, month: str | None = None) -> list[sqlite3.Row]:
    paths = init_ledger(workspace_root, month)
    with sqlite3.connect(paths.path) as connection:
        connection.row_factory = sqlite3.Row
        return list(connection.execute("SELECT * FROM nightly_run ORDER BY id"))


def list_changes(
    workspace_root: Path,
    *,
    month: str | None = None,
    run_id: int | None = None,
) -> list[sqlite3.Row]:
    paths = init_ledger(workspace_root, month)
    query = "SELECT * FROM memory_change"
    values: tuple[object, ...] = ()
    if run_id is not None:
        query += " WHERE run_id = ?"
        values = (run_id,)
    query += " ORDER BY id"
    with sqlite3.connect(paths.path) as connection:
        connection.row_factory = sqlite3.Row
        return list(connection.execute(query, values))


def show_change(workspace_root: Path, *, change_id: int, month: str | None = None) -> sqlite3.Row | None:
    paths = init_ledger(workspace_root, month)
    with sqlite3.connect(paths.path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute("SELECT * FROM memory_change WHERE id = ?", (change_id,)).fetchone()


def _init_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS nightly_run (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_date TEXT NOT NULL,
          started_at TEXT,
          finished_at TEXT,
          result TEXT NOT NULL,
          summary TEXT,
          added_count INTEGER DEFAULT 0,
          updated_count INTEGER DEFAULT 0,
          deleted_count INTEGER DEFAULT 0,
          merged_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS dimension_count (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id INTEGER NOT NULL,
          dimension TEXT NOT NULL,
          count_before INTEGER,
          count_after INTEGER
        );

        CREATE TABLE IF NOT EXISTS memory_change (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id INTEGER NOT NULL,
          action TEXT NOT NULL,
          dimension TEXT NOT NULL,
          memory_no_before INTEGER,
          memory_no_after INTEGER,
          title_before TEXT,
          title_after TEXT,
          content_before TEXT,
          content_after TEXT,
          reason TEXT,
          related_items_json TEXT,
          audit_sources TEXT,
          created_at TEXT NOT NULL
        );
        """
    )


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
