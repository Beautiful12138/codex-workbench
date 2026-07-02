from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ErrorCode, WorkbenchError


@dataclass(frozen=True)
class WriteResult:
    path: Path
    dry_run: bool
    changed: bool


def read_text_utf8(path: str | Path) -> str:
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取 UTF-8 文件失败：{target}",
            exit_code=1,
        ) from exc


def write_text_utf8_atomic(path: str | Path, content: str, *, dry_run: bool = False) -> WriteResult:
    target = Path(path)
    if dry_run:
        return WriteResult(path=target, dry_run=True, changed=False)

    temp_path: Path | None = None

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_path, target)
    except OSError as exc:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"原子写入文件失败：{target}",
            exit_code=1,
        ) from exc

    return WriteResult(path=target, dry_run=False, changed=True)


def read_yaml(path: str | Path) -> Any:
    target = Path(path)
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"YAML 解析失败：{target}",
            exit_code=2,
        ) from exc
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取 YAML 文件失败：{target}",
            exit_code=1,
        ) from exc
    return {} if data is None else data


def write_yaml_atomic(path: str | Path, data: Any, *, dry_run: bool = False) -> WriteResult:
    try:
        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    except yaml.YAMLError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"YAML 序列化失败：{path}",
            exit_code=2,
        ) from exc
    return write_text_utf8_atomic(path, content, dry_run=dry_run)
