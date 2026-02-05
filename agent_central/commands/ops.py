import typer
from agent_central.services.hq_service import HQService
from agent_central.services.git_service import GitService

app = typer.Typer()


@app.command()
def sync():
    """
    Syncs agency state by activating the Task Assigner persona, inspecting repository state, and updating board assignments.
    
    Activates the "task-assigner" persona in HQ; if activation fails the command exits early. When executed inside a Git repository, it reads the current branch. Emits CLI status messages and updates the assignment board (e.g., SQUAD_GOAL.md) as part of the sync process.
    """
    hq = HQService()
    git = GitService()

    typer.echo("ðŸ”„ Syncing Agency Logic...")

    # 1. Switch to Task Assigner
    try:
        hq.set_active_persona("task-assigner")
        typer.echo("âœ… Activated 'Task Assigner' persona.")
    except Exception as e:
        typer.echo(f"âŒ Failed to activate manager: {e}")
        return

    # 2. Basic git status check (Simulation of "Looking at PRs")
    if git.is_git_repo():
        branch = git.get_current_branch()
        typer.echo(f"â„¹ï¸  Current Branch: {branch}")
        # In a real implementation, we would list PRs here
        pass

    typer.echo("ðŸ“‹ Agency synced. Check SQUAD_GOAL.md for assignments.")


@app.command()
def status():
    """Displays current agent status."""
    hq = HQService()
    # Read active persona
    try:
        content = hq.active_persona_file.read_text()
        # Extract first line (Title)
        title = content.split("\n")[0]
        typer.echo(f"ðŸ‘¤ Active Agent: {title}")
    except Exception:
        typer.echo("ðŸ‘¤ Active Agent: None")


@app.command()
def learn():
    """
    Scan the project for learned patterns and sync them to HQ.
    
    Searches the project root for learnable artifacts — including the "## Learned" section in AGENTS.md — and sends discovered knowledge to the HQ service.
    """
    hq = HQService()
    typer.echo("ðŸ§  Initiating Knowledge Feedback Loop...")
    hq.learn_from_project(".")
    typer.echo("ðŸ’¡ New knowledge synced. Run 'ai ops upskill' to consolidate into master roles.")


@app.command()
def upskill():
    """
    Consolidate collected project knowledge into canonical master roles and update agency personas.
    
    Runs the knowledge consolidation process so learned patterns from the repository are merged into master roles and persona definitions are refreshed.
    """
    hq = HQService()
    typer.echo("ðŸš€ Initiating Upskill Protocol (v2.4)...")
    hq.consolidate_knowledge()
    typer.echo("âœ¨ Agency upskilled and evolved.")


@app.command()
def feedback(
    skill: str = typer.Option(..., "--skill", help="Skill ID to provide feedback on"),
    result: str = typer.Option(..., "--result", help="helpful | neutral | harmful"),
    note: str = typer.Option("", "--note", help="Optional context or note"),
):
    """
    Record feedback about a skill for HQ learning and upskilling.
    
    Parameters:
        skill (str): Skill ID to provide feedback for.
        result (str): One of "helpful", "neutral", or "harmful" indicating the feedback outcome.
        note (str): Optional context or note associated with the feedback.
    """
    result = result.lower().strip()
    if result not in {"helpful", "neutral", "harmful"}:
        typer.echo("âŒ Invalid result. Use: helpful | neutral | harmful")
        return
    hq = HQService()
    hq.record_skill_feedback(skill, result, note)