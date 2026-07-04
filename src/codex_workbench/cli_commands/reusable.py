from __future__ import annotations

from pathlib import Path

import typer

from ..errors import WorkbenchError
from ..reusable_memory import (
    find_memories,
    get_memory,
    list_dimension_counts,
    list_dimension_memories,
)
from ..workspace import find_workspace_root
from .common import _exit_with_workbench_error

memory_app = typer.Typer(help="只读检索 docs/reusable 记忆。", no_args_is_help=True)


@memory_app.callback()
def memory_callback() -> None:
    """reusable-memory 命令组。"""


@memory_app.command("list")
def memory_list(
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出所有记忆维度及条数。"""
    try:
        root = find_workspace_root(workspace_root)
        for dimension, count in list_dimension_counts(root):
            typer.echo(f"{dimension}: {count}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


@memory_app.command("show")
def memory_show(
    dimension: str = typer.Argument(..., help="记忆维度。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """列出指定维度的记忆标题。"""
    try:
        root = find_workspace_root(workspace_root)
        for memory in list_dimension_memories(root, dimension):
            typer.echo(f"{memory.number}. {memory.title}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


@memory_app.command("find")
def memory_find(
    keyword: str = typer.Argument(..., help="搜索关键词。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """搜索所有维度的记忆标题和正文。"""
    try:
        root = find_workspace_root(workspace_root)
        for memory in find_memories(root, keyword):
            typer.echo(f"{memory.dimension} {memory.number}. {memory.title}")
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


@memory_app.command("get")
def memory_get(
    dimension: str = typer.Argument(..., help="记忆维度。"),
    number: int = typer.Argument(..., help="记忆编号。"),
    workspace_root: Path = typer.Option(Path("."), "--workspace-root", help="Workbench 根目录。"),
) -> None:
    """读取指定维度中的单条记忆。"""
    try:
        root = find_workspace_root(workspace_root)
        typer.echo(get_memory(root, dimension, number).full_text, nl=False)
    except WorkbenchError as exc:
        _exit_with_workbench_error(exc)


def memory_main() -> None:
    memory_app()
