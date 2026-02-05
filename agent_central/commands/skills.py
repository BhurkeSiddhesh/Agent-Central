import typer
import yaml
from pathlib import Path

from agent_central.models.agency_config import AgencyConfig
from agent_central.services.embedding_service import EmbeddingService
from agent_central.services.hq_service import HQService
from agent_central.services.selection_service import SelectionService
from agent_central.services.profile_service import ProfileService
from agent_central.services.skill_service import SkillService

app = typer.Typer()


@app.command()
def index():
    """
    Scan and index all skills into the HQ skills registry and build corresponding embeddings.
    
    Writes or updates the skills registry file (skills.index.json) and generates or updates embeddings in the HQ storage.
    """
    hq = HQService()
    service = SkillService(hq.hq_path)
    service.build_registry()

    embedder = EmbeddingService(hq.hq_path)
    registry = service.load_registry()
    embedder.load_or_build(registry)


@app.command()
def search(query: str):
    """
    Perform a semantic search for skills matching the provided query and print the results.
    
    Parameters:
        query (str): The search query used to find relevant skills.
    
    Detailed behavior:
        Prints a header with the number of matching skills and then each matched skill's `id` with a high score indicator. If no skills match, prints a message indicating no matches were found.
    """
    hq = HQService()
    service = SkillService(hq.hq_path)
    results = service.search_skills(query)

    if results:
        typer.echo(f"ðŸ” Found {len(results)} skills matching '{query}':")
        for s in results:
            typer.echo(f"  - {s['id']} (Score: High)")
    else:
        typer.echo("âŒ No matching skills found.")


@app.command()
def suggest(
    project: str = typer.Option(".", "--project", help="Path to the project root"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Only print results"),
):
    """
    Suggest a set of skills for a project based on its agency.yaml and optionally persist the selection to .ai-context.
    
    Attempts to read and validate `agency.yaml` in the given project root, performs skill selection, and prints the suggested skills and their scores. If `dry_run` is False, writes the selected profile, manifest, and lockfile into the project's `.ai-context` directory. Exits early and prints a message if the config file is missing or invalid.
    
    Parameters:
        project (str): Path to the project root containing `agency.yaml`.
        dry_run (bool): If True, only print suggestions without writing files.
    """
    project_path = Path(project).resolve()
    config_path = project_path / "agency.yaml"
    if not config_path.exists():
        typer.echo(f"âŒ No 'agency.yaml' found in project: {project_path}")
        return

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        typer.echo(f"âŒ Failed to parse agency config: {e}")
        return

    try:
        config = AgencyConfig.model_validate(raw)
    except Exception as e:
        typer.echo(f"âŒ Invalid agency config: {e}")
        return

    hq = HQService(project_root=str(project_path))
    selector = SelectionService(hq.hq_path, project_path)
    selection = selector.suggest_skills(config)

    typer.echo(f"ðŸ” Suggested {len(selection['selected'])} skills:")
    for s in selection["manifest"]["skills"]:
        typer.echo(f"  - {s['id']} (score: {s['score']})")

    if not dry_run:
        context_root = project_path / ".ai-context"
        profile_service = ProfileService(project_path)
        profile_service.write_profile(selection["profile"], context_root)
        selector.write_manifest(selection["manifest"], context_root)
        selector.write_lock(selection["selected"], selection["scored"], context_root)
        typer.echo("âœ… Profile, manifest, and lockfile written to .ai-context")