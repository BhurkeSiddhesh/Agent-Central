from typing_extensions import Annotated
import typer
from src.services.hq_service import HQService

app = typer.Typer()

@app.command()
def role(
    role_name: str = typer.Argument(None, help="Name of the role to hire (optional if using config)"),
    config: Annotated[str, typer.Option("--config", help="Path to agency.yaml configuration")] = None
):
    """
    Hires an agent or a full team.
    
    - If `role_name` is provided: Activates that specific persona.
    - If `--config` is provided: Hires all agents listed in the config file.
    """
    service = HQService()
    
    if config:
        try:
            typer.echo(f"🔄 Processing agency config: {config}...")
            service.hire_from_config(config)
        except Exception as e:
            typer.echo(f"❌ Error processing config: {e}", err=True)
        return

    if role_name:
        try:
            service.set_active_persona(role_name)
            typer.echo(f"✅ Hired {role_name}. Context updated.")
        except Exception as e:
            typer.echo(f"❌ Error: {e}", err=True)
            typer.echo("Available roles: " + ", ".join(service.list_roles()))
    else:
        typer.echo("ℹ️  Usage: ai hire [ROLE_NAME] or ai hire --config agency.yaml")

