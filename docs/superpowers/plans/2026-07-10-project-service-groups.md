# Project Service Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backward-compatible project grouping for registered services and make `workspace context` list every service name under its project without showing service details by default.

**Architecture:** Extend the existing flat `ServiceEntry` with an optional `project` field, leaving service names and task `service_refs` globally unchanged. Keep writes in the existing service registry writer, add explicit CLI options for setting and clearing groups, and split workspace rendering into a lightweight grouped name overview plus an optional bounded service-check section.

**Tech Stack:** Python 3.11+, Pydantic 2, Typer, PyYAML, pytest, Ruff.

## Global Constraints

- Keep `ServiceRegistry.schema_version` at `0.1`; old registry files without `project` must remain valid.
- Service names remain globally unique and task `service_refs` continue to reference service names only.
- Default `workspace context` must list all registered service names and must not show paths, purpose, notes, Git state, or entry candidates.
- `--check-services` may inspect at most 5 registered services, globally or inside a selected project.
- Do not add root scanning, bulk import, clone, copy, or repository lifecycle behavior.
- Do not add runtime dependencies.
- Do not push the branch or merge into `D:\Work\codex-workbench` before explicit user approval.

---

### Task 1: Service project model and registry writer

**Files:**
- Modify: `src/codex_workbench/models.py`
- Modify: `src/codex_workbench/services.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_services.py`

**Interfaces:**
- Produces: `ServiceEntry.project: NonEmptyString | None`.
- Produces: `ServiceContext.project: str | None`.
- Produces: `add_service(..., project: str | None = None)`.
- Produces: `update_service(..., project: str | None = None, clear_project: bool = False)`.

- [ ] **Step 1: Add failing model and service writer tests**

Add these focused test bodies:

```python
def test_service_registry_accepts_optional_project_and_old_entries() -> None:
    registry = ServiceRegistry.model_validate(
        {
            "schema_version": "0.1",
            "services": [
                {"name": "api", "local_path": "repos/api", "project": "studioV3"},
                {"name": "worker", "local_path": "repos/worker"},
            ],
        }
    )
    assert registry.services[0].project == "studioV3"
    assert registry.services[1].project is None


def test_service_project_can_be_set_and_cleared(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path, project="studioV3")
    assert read_service_registry(tmp_path).services[0].project == "studioV3"

    update_service(tmp_path, name="api", clear_project=True)
    assert read_service_registry(tmp_path).services[0].project is None
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_models.py tests/test_services.py -q
```

Expected: the new tests fail because `ServiceEntry`, `add_service`, and `update_service` do not accept project grouping.

- [ ] **Step 3: Implement the minimal domain support**

Implement these exact interface changes:

```python
class ServiceEntry(WorkbenchModel):
    name: NonEmptyString
    project: NonEmptyString | None = None
    local_path: str | None = None
    purpose: str | None = None
    notes: str | None = None
```

Add `project: str | None` to `ServiceContext`, pass `project` into `ServiceEntry` in `add_service`, and preserve/set/clear it in `update_service`:

```python
if project is not None and clear_project:
    raise WorkbenchError(
        ErrorCode.VALIDATION_ERROR,
        f"service_project_options_conflict: {name}",
        exit_code=2,
    )
if local_path is None and purpose is None and notes is None and project is None and not clear_project:
    raise WorkbenchError(
        ErrorCode.VALIDATION_ERROR,
        f"service_update_no_fields: {name}",
        exit_code=2,
    )
updated_project = None if clear_project else (project if project is not None else current.project)
```

Populate `ServiceContext.project` from the registered entry.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run:

```powershell
py -3 -m pytest tests/test_models.py tests/test_services.py -q
```

Expected: all model and service domain tests pass.

- [ ] **Step 5: Commit the domain change**

```powershell
git add src/codex_workbench/models.py src/codex_workbench/services.py tests/test_models.py tests/test_services.py
git commit -m "feat: add project groups to services"
```

---

### Task 2: Service CLI project management and context output

**Files:**
- Modify: `src/codex_workbench/cli_commands/services.py`
- Modify: `tests/test_cli_service_commands.py`

**Interfaces:**
- Consumes: Task 1 domain signatures.
- Produces: `service add --project`, `service update --project`, and `service update --clear-project`.
- Produces: text `项目：<name|未分组>` and JSON `project` in `service context`.

- [ ] **Step 1: Add failing CLI tests**

Add tests covering the public behavior:

```python
def test_service_cli_sets_and_clears_project(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_result = runner.invoke(
        app,
        ["service", "add", "api", "--path", str(service_path), "--project", "studioV3",
         "--workspace-root", str(tmp_path)],
    )
    assert add_result.exit_code == 0
    grouped = runner.invoke(
        app, ["service", "context", "api", "--format", "json", "--workspace-root", str(tmp_path)]
    )
    assert json.loads(grouped.output)["project"] == "studioV3"

    clear_result = runner.invoke(
        app, ["service", "update", "api", "--clear-project", "--workspace-root", str(tmp_path)]
    )
    assert clear_result.exit_code == 0
    ungrouped = runner.invoke(
        app, ["service", "context", "api", "--workspace-root", str(tmp_path)]
    )
    assert "项目：未分组" in ungrouped.output


def test_service_update_rejects_project_and_clear_project_together(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    runner.invoke(app, ["service", "add", "api", "--path", str(service_path),
                        "--workspace-root", str(tmp_path)])
    result = runner.invoke(
        app, ["service", "update", "api", "--project", "studioV3", "--clear-project",
              "--workspace-root", str(tmp_path)]
    )
    assert result.exit_code == 2
    assert "service_project_options_conflict: api" in combined_output(result)
```

- [ ] **Step 2: Run the CLI tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_cli_service_commands.py -q
```

Expected: Typer rejects the new options and service context lacks project output.

- [ ] **Step 3: Implement minimal CLI options and output**

Add `project` to `service_add`, and add both options to `service_update`:

```python
project: str | None = typer.Option(None, "--project", help="所属项目分组。")
clear_project: bool = typer.Option(False, "--clear-project", help="移除项目分组。")
```

Pass them to the domain functions. Add the project line directly after the service name:

```python
lines = [
    f"服务：{context.name}",
    f"项目：{context.project or '未分组'}",
    f"路径：{path}",
    # existing status and entry lines remain unchanged
]
```

Add `"project": context.project` to `_service_context_payload`.

- [ ] **Step 4: Run the CLI tests and confirm GREEN**

Run:

```powershell
py -3 -m pytest tests/test_cli_service_commands.py tests/test_services.py -q
```

Expected: all service CLI and domain tests pass.

- [ ] **Step 5: Commit the CLI change**

```powershell
git add src/codex_workbench/cli_commands/services.py tests/test_cli_service_commands.py
git commit -m "feat: manage service project groups in cli"
```

---

### Task 3: Grouped workspace context and bounded checks

**Files:**
- Modify: `src/codex_workbench/cli_commands/schema_workspace.py`
- Modify: `tests/test_cli_core.py`

**Interfaces:**
- Produces: `workspace context --project <name>`.
- Produces: `workspace context --ungrouped`.
- Produces: `## 项目与服务概览` with every selected service name.
- Produces: `## 服务检查` only when `--check-services` is present, with at most 5 checked services.

- [ ] **Step 1: Replace the lightweight overview expectations with failing grouped-output tests**

Add a local helper and the following tests to `tests/test_cli_core.py`:

```python
def add_project_services(tmp_path: Path, project: str, names: list[str]) -> None:
    for name in names:
        service_path = tmp_path / "repos" / name
        service_path.mkdir(parents=True)
        result = runner.invoke(
            app,
            [
                "service", "add", name, "--path", str(service_path),
                "--project", project, "--workspace-root", str(tmp_path),
            ],
        )
        assert result.exit_code == 0


def test_workspace_context_groups_all_service_names_without_details(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_names = [f"studio-service-{index:02d}" for index in range(1, 24)]
    add_project_services(tmp_path, "studioV3", service_names)
    ungrouped_path = tmp_path / "repos" / "standalone"
    ungrouped_path.mkdir(parents=True)
    runner.invoke(
        app,
        ["service", "add", "standalone", "--path", str(ungrouped_path),
         "--purpose", "不应出现在默认概览的用途", "--workspace-root", str(tmp_path)],
    )

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "登记项目：1" in result.output
    overview = workspace_context_section(result.output, "## 项目与服务概览", "## 任务焦点")
    assert "- studioV3：23 个服务" in overview
    assert "- 未分组：1 个服务" in overview
    for name in [*service_names, "standalone"]:
        assert f"  - {name}" in overview
    assert "and " not in overview
    assert "路径：" not in overview
    assert "用途：" not in overview
    assert "Git：" not in overview
    assert "registry_only" not in overview


def test_workspace_context_filters_project_and_ungrouped_services(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    add_project_services(tmp_path, "studioV3", ["api", "worker"])
    standalone_path = tmp_path / "repos" / "standalone"
    standalone_path.mkdir(parents=True)
    runner.invoke(
        app, ["service", "add", "standalone", "--path", str(standalone_path),
              "--workspace-root", str(tmp_path)]
    )

    grouped = runner.invoke(
        app, ["workspace", "context", "--project", "studioV3", "--workspace-root", str(tmp_path)]
    )
    ungrouped = runner.invoke(
        app, ["workspace", "context", "--ungrouped", "--workspace-root", str(tmp_path)]
    )

    assert grouped.exit_code == 0
    assert "  - api" in grouped.output
    assert "  - worker" in grouped.output
    assert "standalone" not in workspace_context_section(
        grouped.output, "## 项目与服务概览", "## 任务焦点"
    )
    assert ungrouped.exit_code == 0
    assert "  - standalone" in ungrouped.output
    assert "  - api" not in workspace_context_section(
        ungrouped.output, "## 项目与服务概览", "## 任务焦点"
    )


def test_workspace_context_rejects_invalid_project_filters(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    conflict = runner.invoke(
        app,
        ["workspace", "context", "--project", "studioV3", "--ungrouped",
         "--workspace-root", str(tmp_path)],
    )
    unknown = runner.invoke(
        app,
        ["workspace", "context", "--project", "missing", "--workspace-root", str(tmp_path)],
    )
    assert conflict.exit_code == 2
    assert "workspace_project_options_conflict" in combined_output(conflict)
    assert unknown.exit_code == 2
    assert "unknown_project: missing" in combined_output(unknown)


def test_workspace_context_checks_at_most_five_services_in_selected_project(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    service_names = [f"service-{index}" for index in range(1, 7)]
    add_project_services(tmp_path, "studioV3", service_names)

    result = runner.invoke(
        app,
        ["workspace", "context", "--project", "studioV3", "--check-services",
         "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    overview = workspace_context_section(result.output, "## 项目与服务概览", "## 服务检查")
    checks = workspace_context_section(result.output, "## 服务检查", "## 任务焦点")
    for name in service_names:
        assert f"  - {name}" in overview
    for name in service_names[:5]:
        assert f"- {name}：" in checks
    assert f"- {service_names[5]}：" not in checks
    assert "- and 1 more unchecked services" in checks
```

- [ ] **Step 2: Run workspace CLI tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_cli_core.py -q
```

Expected: tests fail because the old overview shows at most five detailed service rows and the new filters do not exist.

- [ ] **Step 3: Add project selection and grouped name rendering**

Add CLI options:

```python
project_name: str | None = typer.Option(None, "--project", help="只展示指定项目分组。")
ungrouped: bool = typer.Option(False, "--ungrouped", help="只展示未分组服务。")
```

Before rendering, reject both options together with `ErrorCode.VALIDATION_ERROR` and message `workspace_project_options_conflict`. Normalize each raw registry record with:

```python
def _service_project(service: dict[str, object]) -> str | None:
    project = str(service.get("project", "")).strip()
    return project or None
```

Build stable groups in first-appearance order. For a project filter not present in the registry, raise:

```python
raise WorkbenchError(
    ErrorCode.VALIDATION_ERROR,
    f"unknown_project: {project_name}",
    exit_code=2,
)
```

Render every selected service as a nested name-only bullet. Render unknown active service refs in a separate `### 未登记服务引用` block.

- [ ] **Step 4: Separate and bound explicit service checks**

Move the current `service_context` detail construction into `_workspace_service_check_lines`. Select records after the project filter, order them with `_ordered_service_records`, slice `[:5]`, and append `- and N more unchecked services` when selected records remain. Do not call `service_context` at all when `--check-services` is absent.

- [ ] **Step 5: Run workspace and service tests and confirm GREEN**

Run:

```powershell
py -3 -m pytest tests/test_cli_core.py tests/test_cli_service_commands.py tests/test_services.py -q
```

Expected: grouped context, filters, unknown refs, and five-service check limit all pass.

- [ ] **Step 6: Commit workspace grouping**

```powershell
git add src/codex_workbench/cli_commands/schema_workspace.py tests/test_cli_core.py
git commit -m "feat: group workspace services by project"
```

---

### Task 4: Documentation and complete verification

**Files:**
- Modify: `docs/policies/services-and-environment.md`
- Modify: `docs/policies/model-schema.md`
- Modify: `.agents/skills/workbench-cli/SKILL.md`
- Modify: `AGENTS.md`
- Test: complete repository test and lint suites

**Interfaces:**
- Documents: optional project grouping, default full name overview, `--project`, `--ungrouped`, and the five-service explicit check limit.

- [ ] **Step 1: Update user and agent guidance**

Document that `services/registry.yaml` may include optional service project groups; default workspace context lists every service name without inspecting paths; service details require `--service`; explicit checks remain capped at five. Add command examples:

```powershell
codex-workbench service add algorepo --path D:\Work\studio-pass-rebuild-workspace\studioV3\algorepo --project studioV3
codex-workbench service update algorepo --clear-project
codex-workbench workspace context --project studioV3
codex-workbench workspace context --ungrouped
```

Keep the hot-path `AGENTS.md` addition to one concise sentence; do not expand it into a feature manual.

- [ ] **Step 2: Run targeted command help and schema checks**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path src)
py -3 -c "from codex_workbench.cli import main; main()" service add --help
py -3 -c "from codex_workbench.cli import main; main()" service update --help
py -3 -c "from codex_workbench.cli import main; main()" workspace context --help
py -3 -m pytest tests/test_models.py tests/test_services.py tests/test_cli_service_commands.py tests/test_cli_core.py -q
```

Expected: help includes the new options and all focused tests pass.

- [ ] **Step 3: Run complete verification**

Run:

```powershell
py -3 -m pytest -q
py -3 -m ruff check src tests
git diff --check
git status --short
```

Expected: pytest and Ruff exit `0`, diff check is clean, and status contains only the intended documentation changes before their commit.

- [ ] **Step 4: Commit documentation**

```powershell
git add AGENTS.md .agents/skills/workbench-cli/SKILL.md docs/policies/model-schema.md docs/policies/services-and-environment.md docs/superpowers/plans/2026-07-10-project-service-groups.md
git commit -m "docs: explain project-grouped service context"
```

- [ ] **Step 5: Final branch review without push**

Run:

```powershell
git log --oneline main..HEAD
git diff --stat main...HEAD
git status --short
```

Expected: the feature commits are present, the worktree is clean, and no remote push or local merge has occurred.
