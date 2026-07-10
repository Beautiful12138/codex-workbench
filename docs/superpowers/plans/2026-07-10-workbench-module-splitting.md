# Workbench Module Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isolate repository-state contract tests and split the oversized CLI tests, index implementation, and package implementation without changing public behavior.

**Architecture:** Keep `codex_workbench.index` and `codex_workbench.packages` as compatibility facades. Move internal responsibilities into private modules with one-way dependencies, and split CLI tests by command domain while sharing only test construction helpers.

**Tech Stack:** Python 3.11+, pytest, Pydantic 2, Typer, PyYAML, Ruff, Git.

## Global Constraints

- Keep CLI command names, parameters, output text, and exit codes unchanged.
- Keep public Python imports, YAML/Markdown formats, lifecycle gates, and error semantics unchanged.
- Do not change schema version, generated-view content, service registration, or workspace state.
- Do not add runtime dependencies.
- Use `D:\Work\codex-workbench-main` directly; do not create another worktree.
- Preserve every existing behavioral test and compare pytest collection counts after test moves.
- Commit each task independently so it can be reverted without reverting later tasks.

---

## File Structure

### Tests

- `tests/test_structure.py`: file-size regression constraints.
- `tests/cli_test_support.py`: shared `CliRunner`, workspace builders, and CLI assertions.
- `tests/test_cli_core.py`: version, schema, workspace context, index commands, workspace root.
- `tests/test_cli_requirement_task.py`: requirement/task creation, packet update, and prepare commands.
- `tests/test_cli_task_lifecycle.py`: review, implementation, stage, block, obsolete, and gate checks.
- `tests/test_cli_evidence_commands.py`: evidence, validation, and handoff commands.
- `tests/test_cli_task_context.py`: task-context resolution and ability matrix.
- `tests/test_cli_service_commands.py`: service commands.
- `tests/test_cli_material_commands.py`: material, discovery, and intake commands.
- `tests/test_cli_record_commands.py`: action, change, decision, and suspicion commands.
- `tests/test_cli_archive_commands.py`: archive commands.
- `tests/__init__.py`: stable package-relative test support imports.

### Index implementation

- `src/codex_workbench/index.py`: public results and orchestration facade.
- `src/codex_workbench/_index_types.py`: `_YamlRecord` and `_IndexSnapshot`.
- `src/codex_workbench/_index_records.py`: filesystem/YAML loading and snapshot assembly.
- `src/codex_workbench/_index_conflicts.py`: reference and manifest conflict detection.
- `src/codex_workbench/_index_views.py`: CURRENT/index/recovery rendering.

### Package implementation

- `src/codex_workbench/packages.py`: public compatibility exports only.
- `src/codex_workbench/_package_core.py`: result types, shared loading, validation, atomic writing, and rollback support.
- `src/codex_workbench/_package_create.py`: requirement/task creation and requirement closure.
- `src/codex_workbench/_package_tasks.py`: task packet, stage, prepare, impact, document, block, and obsolete operations.

---

### Task 1: Isolate Repository Contracts and Add Structural Red Tests

**Files:**
- Create: `tests/test_structure.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_codex_integration.py`

**Interfaces:**
- Consumes: `ServiceRegistry.model_validate(data: object) -> ServiceRegistry`.
- Produces: explicit unit data for registry parsing, one repository contract test, and structural constraints that drive Tasks 2-4.

- [ ] **Step 1: Replace the registry unit test with inline non-empty data**

Remove `ROOT`, `Path`, and the YAML file read from `tests/test_models.py`. Use this test body:

```python
def test_service_registry_accepts_registered_services() -> None:
    registry = ServiceRegistry.model_validate(
        {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "services": [
                {
                    "name": "user-api",
                    "local_path": r"D:\Work\services\user-api",
                    "purpose": "用户接口服务",
                }
            ],
        }
    )

    assert registry.schema_version == CURRENT_SCHEMA_VERSION
    assert registry.services[0].name == "user-api"
    assert registry.services[0].purpose == "用户接口服务"
```

- [ ] **Step 2: Add the intentional repository registry contract**

Add `ServiceRegistry` to the imports in `tests/test_codex_integration.py`, then add:

```python
def test_repository_service_registry_matches_current_schema() -> None:
    registry_path = PROJECT_ROOT / "services" / "registry.yaml"
    registry_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    registry = ServiceRegistry.model_validate(registry_data)

    assert registry.schema_version == "0.1"
```

This test deliberately reads a repository asset but does not assert mutable service content.

- [ ] **Step 3: Write structural constraints**

Create `tests/test_structure.py`:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_public_facades_stay_focused() -> None:
    limits = {"index.py": 220, "packages.py": 220}
    oversized = {
        filename: _line_count(ROOT / "src" / "codex_workbench" / filename)
        for filename, limit in limits.items()
        if _line_count(ROOT / "src" / "codex_workbench" / filename) > limit
    }

    assert oversized == {}


def test_runtime_modules_stay_within_reviewable_size() -> None:
    oversized = {
        path.relative_to(ROOT).as_posix(): _line_count(path)
        for path in sorted((ROOT / "src" / "codex_workbench").glob("*.py"))
        if _line_count(path) > 700
    }

    assert oversized == {}


def test_cli_test_modules_stay_within_reviewable_size() -> None:
    oversized = {
        path.relative_to(ROOT).as_posix(): _line_count(path)
        for path in sorted((ROOT / "tests").glob("test_cli*.py"))
        if _line_count(path) > 1_200
    }

    assert oversized == {}
```

- [ ] **Step 4: Run the focused tests and verify the intended red state**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_models.py tests/test_codex_integration.py tests/test_structure.py -q -p no:cacheprovider
```

Expected: registry tests pass; the three structure tests fail, reporting `index.py`, `packages.py`, and `test_cli.py` as oversized.

- [ ] **Step 5: Commit the test isolation and red constraints**

```powershell
git add -- tests/test_models.py tests/test_codex_integration.py tests/test_structure.py
git commit -m "Test repository contracts independently"
```

---

### Task 2: Split CLI Tests by Command Domain

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/cli_test_support.py`
- Create: the nine `tests/test_cli_*.py` domain files listed in File Structure
- Delete: `tests/test_cli.py`

**Interfaces:**
- Consumes: `codex_workbench.cli.app` and the existing assertions from `tests/test_cli.py`.
- Produces: the same CLI behavioral tests with stable imports from `tests.cli_test_support`.

- [ ] **Step 1: Capture the pre-move CLI test collection**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_cli.py --collect-only -q -p no:cacheprovider
```

Expected: 120 CLI tests collected. Save the displayed node IDs for comparison during Step 5; parameterized cases remain represented by their node IDs.

- [ ] **Step 2: Create the shared support module**

Move these definitions unchanged from the start of `test_cli.py` into `tests/cli_test_support.py`:

```python
runner = CliRunner()

def create_workspace(root: Path) -> None: ...
def write_requirement(root: Path, *, status: str = "readable", confirmed_by_user: bool = True) -> None: ...
def combined_output(result) -> str: ...
def assert_markdown_template_hint(output: str) -> None: ...
def workspace_context_section(output: str, start: str, end: str) -> str: ...
def create_task_via_cli(root: Path, extra_args: list[str] | None = None): ...
```

Rename `_workspace_context_section` to `workspace_context_section` and update its callers. `tests/__init__.py` is an empty file.

- [ ] **Step 3: Move tests into domain files without changing bodies**

Use the original function boundaries:

| Destination | Original range |
| --- | --- |
| `test_cli_core.py` | `test_version_command_prints_package_name` through `test_workspace_root_command_reports_missing_workspace` |
| `test_cli_requirement_task.py` | `test_requirement_create_command_writes_package` through `test_task_prepare_merges_partial_impact_profile_update` |
| `test_cli_task_lifecycle.py` | `test_task_review_and_implementation_create_use_package_local_docs` through `test_task_obsolete_command_sets_stage_with_reason` |
| `test_cli_evidence_commands.py` | `test_evidence_validation_handoff_commands_allow_done` through `test_handoff_waiting_blocks_done_command` |
| `test_cli_task_context.py` | `test_task_context_resolves_task_by_title_and_uses_names` through `test_task_context_rejects_unsupported_format_before_loading_workspace` |
| `test_cli_service_commands.py` | `test_service_add_and_list_commands_manage_registry` through `test_service_context_command_rejects_unknown_service` |
| `test_cli_material_commands.py` | `test_material_add_and_list_commands_manage_inbox_registry` through `test_intake_confirm_dry_run_does_not_change_readiness` |
| `test_cli_record_commands.py` | `test_action_create_writes_machine_record_and_does_not_touch_task` through `test_change_decision_suspicion_negative_guards` |
| `test_cli_archive_commands.py` | `write_archive_ready_requirement` through the end of the file |

Each file imports `app` plus only the standard-library, PyYAML, and support symbols used by its moved tests. Use this support import shape and let Ruff remove unused names:

```python
from tests.cli_test_support import (
    assert_markdown_template_hint,
    combined_output,
    create_task_via_cli,
    create_workspace,
    runner,
    workspace_context_section,
    write_requirement,
)
```

- [ ] **Step 4: Remove the original file and normalize imports**

Delete `tests/test_cli.py`, then run:

```powershell
$cliTests = Get-ChildItem -LiteralPath tests -Filter 'test_cli_*.py' | ForEach-Object { $_.FullName }
python -m ruff check --fix --no-cache tests/cli_test_support.py @cliTests
python -m ruff format --no-cache tests/cli_test_support.py @cliTests
```

Expected: unused imports removed and formatting succeeds without behavioral edits.

- [ ] **Step 5: Verify collection and CLI behavior**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$cliTests = Get-ChildItem -LiteralPath tests -Filter 'test_cli_*.py' | ForEach-Object { $_.FullName }
python -m pytest @cliTests --collect-only -q -p no:cacheprovider
python -m pytest @cliTests -q -p no:cacheprovider
python -m pytest tests/test_structure.py -q -p no:cacheprovider
```

Expected: the moved CLI node IDs are all present, 120 CLI tests pass, and the two source-module structure tests remain red.

- [ ] **Step 6: Commit the CLI test split**

```powershell
git add -- tests/__init__.py tests/cli_test_support.py tests/test_cli.py tests/test_cli_*.py
git commit -m "Split CLI tests by command domain"
```

---

### Task 3: Split Index Collection, Conflict Detection, and Rendering

**Files:**
- Create: `src/codex_workbench/_index_types.py`
- Create: `src/codex_workbench/_index_records.py`
- Create: `src/codex_workbench/_index_conflicts.py`
- Create: `src/codex_workbench/_index_views.py`
- Modify: `src/codex_workbench/index.py`
- Modify: `src/codex_workbench/cli_commands/schema_workspace.py`

**Interfaces:**
- Consumes: workspace paths and YAML records.
- Produces: unchanged `IndexWriteResult`, `IndexCheckResult`, `generate_index_views`, and `check_generated_views` from `codex_workbench.index`.

- [ ] **Step 1: Extract internal types**

Move `_YamlRecord` and `_IndexSnapshot` unchanged into `_index_types.py`. Import `Any` and `Path`; expose no `__all__` because both names remain private.

- [ ] **Step 2: Extract conflict detection**

Move `_record_errors` through `_archive_manifest_conflicts` into `_index_conflicts.py` and add this orchestrator:

```python
def collect_conflicts(
    requirements: list[_YamlRecord],
    tasks: list[_YamlRecord],
    evidences: list[_YamlRecord],
    archives: list[_YamlRecord],
    services: list[dict[str, Any]],
    record_groups: list[tuple[str, list[_YamlRecord]]],
) -> list[str]:
    conflicts: list[str] = []
    for kind, records in record_groups:
        conflicts.extend(_record_errors(records))
        conflicts.extend(_duplicate_id_conflicts(records, kind))
        conflicts.extend(_path_id_conflicts(records, kind))
        conflicts.extend(_file_id_conflicts(records, kind))
    conflicts.extend(_task_ref_conflicts(requirements, tasks))
    conflicts.extend(_service_ref_conflicts(tasks, services))
    conflicts.extend(_evidence_conflicts(tasks, evidences))
    conflicts.extend(_archive_manifest_conflicts(archives))
    return list(dict.fromkeys(conflicts))
```

Preserve conflict ordering and deduplication exactly as the original `_collect_snapshot` implementation.

- [ ] **Step 3: Extract record loading and snapshot assembly**

Move `_collect_snapshot`, `_read_records`, `_read_materials`, `_read_services`, and `_load_yaml_dict` into `_index_records.py`. Rename `_collect_snapshot` to `collect_snapshot` and call `collect_conflicts` for the conflict list. Keep glob patterns and record ordering unchanged.

- [ ] **Step 4: Extract all render functions**

Move `_record_link` through `_final_newline` into `_index_views.py`, together with rendering limits and `REDACT_MARKERS`. Rename only the three facade entry points:

```python
render_current = _render_current
render_index = _render_index
render_recovery = _render_recovery
```

Keep helper names private and keep returned text byte-for-byte identical.

- [ ] **Step 5: Reduce `index.py` to orchestration**

Keep path constants and public result dataclasses in `index.py`. Import private components and implement the public functions with the original write/check logic:

```python
from ._index_records import collect_snapshot
from ._index_views import render_current, render_index, render_recovery

snapshot = collect_snapshot(root)
current_text = render_current(snapshot)
index_text = render_index(snapshot)
recovery_text = render_recovery(snapshot)
```

Do not change write order, dry-run behavior, stale messages, or `conflicts` return values.

- [ ] **Step 6: Point workspace context at the internal index modules**

Import `_IndexSnapshot` and `_YamlRecord` from `_index_types`, `collect_snapshot` from `_index_records`, and the three display helpers from `_index_views`. Replace `_collect_snapshot(root)` with `collect_snapshot(root)`. Do not re-export these private names from `index.py`.

- [ ] **Step 7: Verify index behavior and the remaining package-size red state**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_index.py tests/test_doctor.py tests/test_cli_core.py tests/test_codex_integration.py -q -p no:cacheprovider
python -m pytest tests/test_structure.py::test_public_facades_stay_focused tests/test_structure.py::test_runtime_modules_stay_within_reviewable_size -q -p no:cacheprovider
$indexModules = Get-ChildItem -LiteralPath src/codex_workbench -Filter '_index_*.py' | ForEach-Object { $_.FullName }
python -m ruff check --no-cache src/codex_workbench/index.py @indexModules
```

Expected after this task: index-related tests pass; the runtime size test still reports only `packages.py` until Task 4.

- [ ] **Step 8: Commit the index split**

```powershell
git add -- docs/superpowers/specs/2026-07-10-workbench-module-splitting-design.md docs/superpowers/plans/2026-07-10-workbench-module-splitting.md src/codex_workbench/index.py src/codex_workbench/_index_types.py src/codex_workbench/_index_records.py src/codex_workbench/_index_conflicts.py src/codex_workbench/_index_views.py src/codex_workbench/cli_commands/schema_workspace.py
git commit -m "Split index generation responsibilities"
```

---

### Task 4: Split Package Creation and Task Mutation Responsibilities

**Files:**
- Create: `src/codex_workbench/_package_core.py`
- Create: `src/codex_workbench/_package_create.py`
- Create: `src/codex_workbench/_package_tasks.py`
- Modify: `src/codex_workbench/packages.py`
- Modify: `tests/test_packages.py`

**Interfaces:**
- Consumes: the existing templates, models, lifecycle evaluators, service registry, and atomic I/O helpers.
- Produces: every current public name from `codex_workbench.packages` with unchanged signatures and return types.

- [ ] **Step 1: Extract shared package core**

Move these items into `_package_core.py`:

```text
INITIAL_CREATE_STAGES
FINAL_CREATE_STAGES
PackageWriteResult
TaskStageCheckResult
RequirementTaskRefUpdate
write_package_files
_has_path_traversal
_validate_new_package_id
_package_file
_load_task_package
_clean_required
_clean_list
_clean_required_list
_apply_task_impact_update
_assert_known_service_refs
_assert_task_id_matches_requirement
_assert_requirement_allows_task
_prepare_requirement_task_ref_update
_expected_file_contents
_rollback_created_files
```

Keep the original implementations unchanged. Domain modules import the module as:

```python
from . import _package_core as package_core
```

and call shared I/O through `package_core`, preserving one monkeypatch seam.

- [ ] **Step 2: Extract requirement and task creation**

Move `create_requirement_package`, `create_task_package`, and `close_requirement` into `_package_create.py`. Replace each reference to a moved helper or result type with the same attribute name on `package_core`. Keep YAML validation, requirement ref updates, rollback, and optimistic versions unchanged.

- [ ] **Step 3: Extract task mutations**

Move these functions into `_package_tasks.py`:

```text
update_task_packet
set_task_stage
check_task_stage
prepare_task
update_task_impact
create_task_review_document
create_task_implementation_document
block_task
obsolete_task
```

Replace each moved-helper and I/O reference with the same attribute name on `package_core`. Keep the lazy import of `assert_done_evidence_valid` inside stage functions to avoid changing import order.

- [ ] **Step 4: Create the compatibility facade**

Replace `packages.py` with explicit re-exports:

```python
from ._package_core import PackageWriteResult, RequirementTaskRefUpdate, TaskStageCheckResult, write_package_files
from ._package_create import close_requirement, create_requirement_package, create_task_package
from ._package_tasks import (
    block_task,
    check_task_stage,
    create_task_implementation_document,
    create_task_review_document,
    obsolete_task,
    prepare_task,
    set_task_stage,
    update_task_impact,
    update_task_packet,
)

__all__ = [
    "PackageWriteResult",
    "RequirementTaskRefUpdate",
    "TaskStageCheckResult",
    "block_task",
    "check_task_stage",
    "close_requirement",
    "create_requirement_package",
    "create_task_implementation_document",
    "create_task_package",
    "create_task_review_document",
    "obsolete_task",
    "prepare_task",
    "set_task_stage",
    "update_task_impact",
    "update_task_packet",
    "write_package_files",
]
```

- [ ] **Step 5: Retarget internal monkeypatch tests**

In `tests/test_packages.py`, replace `import codex_workbench.packages as packages_module` with:

```python
import codex_workbench._package_core as package_core_module
```

Change the four patch targets:

```python
monkeypatch.setattr(package_core_module, "write_text_utf8_atomic", fail_on_markdown)
monkeypatch.setattr(package_core_module, "write_text_utf8_atomic", fail_on_second)
monkeypatch.setattr(package_core_module, "read_yaml_with_version", read_stale_snapshot)
monkeypatch.setattr(package_core_module, "write_yaml_atomic", fail_after_external_review_edit)
```

- [ ] **Step 6: Verify package behavior, public compatibility, and all structure constraints**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_packages.py tests/test_validation.py tests/test_materials.py tests/test_cli_requirement_task.py tests/test_cli_task_lifecycle.py tests/test_cli_task_context.py tests/test_codex_integration.py -q -p no:cacheprovider
python -m pytest tests/test_structure.py -q -p no:cacheprovider
python -c "from codex_workbench.packages import PackageWriteResult, check_task_stage, create_task_package, set_task_stage"
$packageModules = Get-ChildItem -LiteralPath src/codex_workbench -Filter '_package_*.py' | ForEach-Object { $_.FullName }
python -m ruff check --no-cache src/codex_workbench/packages.py @packageModules tests/test_packages.py
```

Expected: all focused tests and all three structure tests pass; the import command exits with code 0.

- [ ] **Step 7: Commit the package split**

```powershell
git add -- src/codex_workbench/packages.py src/codex_workbench/_package_core.py src/codex_workbench/_package_create.py src/codex_workbench/_package_tasks.py tests/test_packages.py
git commit -m "Split package lifecycle responsibilities"
```

---

### Task 5: Final Verification and Diff Review

**Files:**
- Verify only; modify files only if a failure is directly caused by Tasks 1-4.

**Interfaces:**
- Consumes: all commits from Tasks 1-4.
- Produces: fresh evidence that behavior, style, collection, and repository scope remain correct.

- [ ] **Step 1: Run the complete test suite**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
```

Expected: 350 tests pass: 346 baseline tests, three structure constraints, and one explicit repository registry contract.

- [ ] **Step 2: Run Ruff and import checks**

```powershell
python -m ruff check --no-cache src tests
$indexModules = Get-ChildItem -LiteralPath src/codex_workbench -Filter '_index_*.py' | ForEach-Object { $_.FullName }
$packageModules = Get-ChildItem -LiteralPath src/codex_workbench -Filter '_package_*.py' | ForEach-Object { $_.FullName }
$cliTests = Get-ChildItem -LiteralPath tests -Filter 'test_cli_*.py' | ForEach-Object { $_.FullName }
python -m ruff format --check --no-cache src/codex_workbench/index.py src/codex_workbench/packages.py @indexModules @packageModules tests/test_structure.py tests/cli_test_support.py @cliTests
python -c "from codex_workbench.index import check_generated_views, generate_index_views; from codex_workbench.packages import check_task_stage, create_task_package"
```

Expected: all commands exit with code 0.

- [ ] **Step 3: Recheck collection and file sizes**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest --collect-only -q -p no:cacheprovider
python -m pytest tests/test_structure.py -q -p no:cacheprovider
```

Expected: 350 tests collected and all three structure tests pass.

- [ ] **Step 4: Review repository scope**

```powershell
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git status --short
```

Expected: only design/plan docs, the named test files, and the named source modules changed; no generated views, service registry, active YAML, or user brief/handoff files changed.

- [ ] **Step 5: Stop on unexpected verification failures**

If Steps 1-4 reveal a failure not already covered by a task's focused verification, stop and investigate the failure separately before modifying more files. If no correction is required, do not create an empty commit.
