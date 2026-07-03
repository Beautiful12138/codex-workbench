from __future__ import annotations

import typer

from . import __version__
from .cli_commands.archive import archive_app
from .cli_commands.evidence import evidence_app, handoff_app, validation_app
from .cli_commands.index_doctor import doctor_app, index_app
from .cli_commands.materials import discovery_app, intake_app, material_app
from .cli_commands.records import action_app, change_app, decision_app, suspicion_app
from .cli_commands.requirement_task import requirement_app, task_app
from .cli_commands.schema_workspace import schema_app, workspace_app
from .cli_commands.services import service_app


app = typer.Typer(help="个人本地 Codex workbench 工具。")
app.add_typer(schema_app, name="schema")
app.add_typer(workspace_app, name="workspace")
app.add_typer(requirement_app, name="requirement")
app.add_typer(task_app, name="task")
app.add_typer(service_app, name="service")
app.add_typer(material_app, name="material")
app.add_typer(discovery_app, name="discovery")
app.add_typer(intake_app, name="intake")
app.add_typer(evidence_app, name="evidence")
app.add_typer(validation_app, name="validation")
app.add_typer(handoff_app, name="handoff")
app.add_typer(action_app, name="action")
app.add_typer(change_app, name="change")
app.add_typer(decision_app, name="decision")
app.add_typer(suspicion_app, name="suspicion")
app.add_typer(index_app, name="index")
app.add_typer(doctor_app, name="doctor")
app.add_typer(archive_app, name="archive")


@app.command()
def version() -> None:
    """打印版本。"""
    typer.echo(f"codex-workbench {__version__}")


def main() -> None:
    app()
