import typer
from src.services.hq_service import HQService

app = typer.Typer()

@app.command()
def role(role_name: str):
    """
    Manually switches the active persona (e.g., 'backend-dev', 'jules-qa').
    """
    service = HQService()
    try:
        service.set_active_persona(role_name)
        typer.echo(f"✅ Hired {role_name}. Context updated.")
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        typer.echo("Available roles: " + ", ".join(service.list_roles()))
