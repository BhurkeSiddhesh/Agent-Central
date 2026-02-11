import os
from pathlib import Path

import typer
from typing_extensions import Annotated

from agent_central.services.hq_service import HQService

app = typer.Typer()


@app.command()
def project(
    hq_source: Annotated[
        str, typer.Option("--hq", help="Path to the HQ source (local path)")
    ] = "agency-hq",
):
    """
    Initializes the AI-Ops project structure.
    Bootstraps .agency-hq and .ai-context.
    """
    service = HQService()
    try:
        typer.echo(f"🚀 Initializing AI-Ops Project...")
        service.setup_hq(hq_source)
        typer.echo("✅ Agency HQ installed.")
        typer.echo("✅ .ai-context initialized.")
        typer.echo("ℹ️  Run 'ai hire task-assigner' to start the manager.")
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
