from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    WORKSPACE_NOT_FOUND = "workspace_not_found"
    PATH_OUTSIDE_WORKSPACE = "path_outside_workspace"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    IO_ERROR = "io_error"


class WorkbenchError(Exception):
    def __init__(self, code: ErrorCode, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message
