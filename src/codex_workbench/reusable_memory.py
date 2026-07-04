from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import ErrorCode, WorkbenchError
from .io import read_text_utf8

REUSABLE_DIMENSIONS = (
    "workflow",
    "services",
    "validation",
    "architecture",
    "environment",
    "patterns",
    "pitfalls",
)

_MEMORY_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")


@dataclass(frozen=True)
class ReusableMemory:
    dimension: str
    number: int
    title: str
    body: str

    @property
    def full_text(self) -> str:
        return f"## {self.number}. {self.title}\n\n{self.body}".rstrip() + "\n"


def reusable_root(workspace_root: Path) -> Path:
    return workspace_root / "docs" / "reusable"


def dimension_path(workspace_root: Path, dimension: str) -> Path:
    _ensure_dimension(dimension)
    return reusable_root(workspace_root) / f"{dimension}.md"


def parse_dimension_file(path: Path, dimension: str) -> list[ReusableMemory]:
    if not path.exists():
        return []
    text = read_text_utf8(path)
    lines = text.splitlines()
    starts: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = _MEMORY_HEADING_RE.match(line)
        if match:
            starts.append((index, int(match.group(1)), match.group(2).strip()))

    memories: list[ReusableMemory] = []
    for position, (start_index, number, title) in enumerate(starts):
        end_index = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body_lines = lines[start_index + 1 : end_index]
        body = "\n".join(body_lines).strip()
        memories.append(ReusableMemory(dimension=dimension, number=number, title=title, body=body))
    return memories


def list_dimension_counts(workspace_root: Path) -> list[tuple[str, int]]:
    return [
        (dimension, len(parse_dimension_file(dimension_path(workspace_root, dimension), dimension)))
        for dimension in REUSABLE_DIMENSIONS
    ]


def list_dimension_memories(workspace_root: Path, dimension: str) -> list[ReusableMemory]:
    return parse_dimension_file(dimension_path(workspace_root, dimension), dimension)


def get_memory(workspace_root: Path, dimension: str, number: int) -> ReusableMemory:
    for memory in list_dimension_memories(workspace_root, dimension):
        if memory.number == number:
            return memory
    raise WorkbenchError(
        ErrorCode.VALIDATION_ERROR,
        f"memory_not_found: {dimension} {number}",
        exit_code=1,
    )


def find_memories(workspace_root: Path, keyword: str) -> list[ReusableMemory]:
    normalized = keyword.casefold().strip()
    if not normalized:
        raise WorkbenchError(ErrorCode.VALIDATION_ERROR, "keyword_required", exit_code=1)

    matches: list[ReusableMemory] = []
    for dimension in REUSABLE_DIMENSIONS:
        for memory in list_dimension_memories(workspace_root, dimension):
            haystack = f"{memory.title}\n{memory.body}".casefold()
            if normalized in haystack:
                matches.append(memory)
    return matches


def _ensure_dimension(dimension: str) -> None:
    if dimension not in REUSABLE_DIMENSIONS:
        allowed = ", ".join(REUSABLE_DIMENSIONS)
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_dimension: {dimension} (allowed: {allowed})",
            exit_code=1,
        )
