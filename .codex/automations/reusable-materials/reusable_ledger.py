from __future__ import annotations

import sys
from pathlib import Path

import typer

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from codex_workbench.errors import WorkbenchError  # noqa: E402
from codex_workbench.reusable_ledger import (  # noqa: E402
    add_change,
    add_dimension_count,
    add_run,
    init_ledger,
    list_changes,
    list_runs,
    show_change,
    update_run,
)
from codex_workbench.workspace import find_workspace_root  # noqa: E402


app = typer.Typer(help="夜间私有 reusable 记忆 SQLite 账本。", no_args_is_help=True)


def _exit_with_error(exc: WorkbenchError) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(exc.exit_code)


@app.command("init")
def ledger_init(
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """初始化当月 SQLite 账本。"""
    try:
        root = find_workspace_root(workspace_root)
        paths = init_ledger(root, month)
        typer.echo(paths.path.relative_to(root).as_posix())
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("add-run")
def ledger_add_run(
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    run_date: str | None = typer.Option(None, "--run-date", help="运行日期 YYYY-MM-DD。"),
    started_at: str | None = typer.Option(None, "--started-at", help="开始时间。"),
    result: str = typer.Option("partial", "--result", help="运行结果。"),
    summary: str | None = typer.Option(None, "--summary", help="简短总结。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """新增一条夜间运行记录。"""
    try:
        root = find_workspace_root(workspace_root)
        run_id = add_run(
            root,
            month=month,
            run_date=run_date,
            started_at=started_at,
            result=result,
            summary=summary,
        )
        typer.echo(str(run_id))
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("update-run")
def ledger_update_run(
    run_id: int = typer.Option(..., "--run-id", help="nightly_run.id。"),
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    finished_at: str | None = typer.Option(None, "--finished-at", help="结束时间。"),
    result: str | None = typer.Option(None, "--result", help="运行结果。"),
    summary: str | None = typer.Option(None, "--summary", help="简短总结。"),
    added_count: int | None = typer.Option(None, "--added-count", help="新增数量。"),
    updated_count: int | None = typer.Option(None, "--updated-count", help="更新数量。"),
    deleted_count: int | None = typer.Option(None, "--deleted-count", help="删除数量。"),
    merged_count: int | None = typer.Option(None, "--merged-count", help="合并数量。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """更新夜间运行记录。"""
    try:
        root = find_workspace_root(workspace_root)
        update_run(
            root,
            run_id=run_id,
            month=month,
            finished_at=finished_at,
            result=result,
            summary=summary,
            added_count=added_count,
            updated_count=updated_count,
            deleted_count=deleted_count,
            merged_count=merged_count,
        )
        typer.echo(f"updated run {run_id}")
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("add-dimension-count")
def ledger_add_dimension_count(
    run_id: int = typer.Option(..., "--run-id", help="nightly_run.id。"),
    dimension: str = typer.Option(..., "--dimension", help="记忆维度。"),
    count_before: int | None = typer.Option(None, "--count-before", help="维护前数量。"),
    count_after: int | None = typer.Option(None, "--count-after", help="维护后数量。"),
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """新增维度数量记录。"""
    try:
        root = find_workspace_root(workspace_root)
        record_id = add_dimension_count(
            root,
            run_id=run_id,
            dimension=dimension,
            count_before=count_before,
            count_after=count_after,
            month=month,
        )
        typer.echo(str(record_id))
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("add-change")
def ledger_add_change(
    run_id: int = typer.Option(..., "--run-id", help="nightly_run.id。"),
    action: str = typer.Option(..., "--action", help="add/update/delete/merge/reorder/skip。"),
    dimension: str = typer.Option(..., "--dimension", help="记忆维度。"),
    memory_no_before: int | None = typer.Option(None, "--memory-no-before", help="修改前编号。"),
    memory_no_after: int | None = typer.Option(None, "--memory-no-after", help="修改后编号。"),
    title_before: str | None = typer.Option(None, "--title-before", help="修改前标题。"),
    title_after: str | None = typer.Option(None, "--title-after", help="修改后标题。"),
    reason: str | None = typer.Option(None, "--reason", help="变更原因。"),
    audit_sources_json: str | None = typer.Option(None, "--audit-sources-json", help="审计来源 JSON。"),
    content_before: str | None = typer.Option(None, "--content-before", help="修改前记忆全文。"),
    content_after: str | None = typer.Option(None, "--content-after", help="修改后记忆全文。"),
    related_items_json: str | None = typer.Option(None, "--related-items-json", help="关联旧记忆 JSON。"),
    content_before_file: Path | None = typer.Option(None, "--content-before-file", help="修改前全文文件。"),
    content_after_file: Path | None = typer.Option(None, "--content-after-file", help="修改后全文文件。"),
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """新增单条记忆变更记录。"""
    try:
        root = find_workspace_root(workspace_root)
        record_id = add_change(
            root,
            run_id=run_id,
            action=action,
            dimension=dimension,
            memory_no_before=memory_no_before,
            memory_no_after=memory_no_after,
            title_before=title_before,
            title_after=title_after,
            content_before=content_before,
            content_after=content_after,
            content_before_file=content_before_file,
            content_after_file=content_after_file,
            reason=reason,
            related_items_json=related_items_json,
            audit_sources=audit_sources_json,
            month=month,
        )
        typer.echo(str(record_id))
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("list-runs")
def ledger_list_runs(
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出夜间运行记录。"""
    try:
        root = find_workspace_root(workspace_root)
        for row in list_runs(root, month=month):
            typer.echo(
                f"{row['id']} {row['run_date']} {row['result']} "
                f"add={row['added_count']} update={row['updated_count']} "
                f"delete={row['deleted_count']} merge={row['merged_count']}"
            )
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("list-changes")
def ledger_list_changes(
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    run_id: int | None = typer.Option(None, "--run-id", help="只列出指定 run。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出记忆变更记录。"""
    try:
        root = find_workspace_root(workspace_root)
        for row in list_changes(root, month=month, run_id=run_id):
            title = row["title_after"] or row["title_before"] or ""
            typer.echo(f"{row['id']} run={row['run_id']} {row['action']} {row['dimension']} {title}")
    except WorkbenchError as exc:
        _exit_with_error(exc)


@app.command("show-change")
def ledger_show_change(
    change_id: int = typer.Argument(..., help="memory_change.id。"),
    month: str | None = typer.Option(None, "--month", help="账本月份 YYYY-MM；默认当前月。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """显示单条记忆变更详情。"""
    try:
        root = find_workspace_root(workspace_root)
        row = show_change(root, change_id=change_id, month=month)
        if row is None:
            typer.echo(f"change_not_found: {change_id}", err=True)
            raise typer.Exit(1)
        for key in row.keys():
            value = row[key]
            if value is not None:
                typer.echo(f"{key}: {value}")
    except WorkbenchError as exc:
        _exit_with_error(exc)


if __name__ == "__main__":
    app()
