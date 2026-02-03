import typer
from src.services.hq_service import HQService
from src.services.git_service import GitService

app = typer.Typer()

@app.command()
def sync():
    """
    Runs the 'Task Assigner' protocol (formerly ai sync).
    Checks for PRs/branches and updates the Board.
    """
    hq = HQService()
    git = GitService()

    typer.echo("🔄 Syncing Agency Logic...")
    
    # 1. Switch to Task Assigner
    try:
        hq.set_active_persona("task-assigner")
        typer.echo("✅ Activated 'Task Assigner' persona.")
    except Exception as e:
        typer.echo(f"❌ Failed to activate manager: {e}")
        return

    # 2. Basic git status check (Simulation of "Looking at PRs")
    if git.is_git_repo():
        branch = git.get_current_branch()
        typer.echo(f"ℹ️  Current Branch: {branch}")
        # In a real implementation, we would list PRs here
        pass
    
    typer.echo("📋 Agency synced. Check SQUAD_GOAL.md for assignments.")

@app.command()
def status():
    """Displays current agent status."""
    hq = HQService()
    # Read active persona
    try:
        content = hq.active_persona_file.read_text()
        # Extract first line (Title)
        title = content.split('\n')[0]
        typer.echo(f"👤 Active Agent: {title}")
    except:
        typer.echo("👤 Active Agent: None")
