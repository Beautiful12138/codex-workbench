from __future__ import annotations

from workbench_common import emit_context, find_workspace_root, read_payload, user_prompt_context


def main() -> None:
    payload = read_payload()
    root = find_workspace_root(payload)
    emit_context("UserPromptSubmit", user_prompt_context(root))


if __name__ == "__main__":
    main()
