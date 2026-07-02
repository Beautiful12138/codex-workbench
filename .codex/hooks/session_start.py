from __future__ import annotations

from workbench_common import emit_context, find_workspace_root, read_payload, session_start_context


def main() -> None:
    payload = read_payload()
    root = find_workspace_root(payload)
    emit_context("SessionStart", session_start_context(root))


if __name__ == "__main__":
    main()
