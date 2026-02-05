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
    """Scans and indexes all skills into skills.index.json + embeddings."""
    hq = HQService()
    service = SkillService(hq.hq_path)
    service.build_registry()

    embedder = EmbeddingService(hq.hq_path)
    registry = service.load_registry()
    embedder.load_or_build(registry)


@app.command()
def search(query: str):
    """Semantic search for skills."""
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
    """Suggests a skill set for a project without copying files."""
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
