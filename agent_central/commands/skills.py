import typer
from agent_central.services.skill_service import SkillService
from agent_central.services.hq_service import HQService

app = typer.Typer()

@app.command()
def index():
    """Scans and indexes all skills into skills.json."""
    hq = HQService()
    service = SkillService(hq.hq_path)
    service.build_registry()

@app.command()
def search(query: str):
    """Semantic search for skills."""
    hq = HQService()
    service = SkillService(hq.hq_path)
    results = service.search_skills(query)
    
    if results:
        typer.echo(f"🔍 Found {len(results)} skills matching '{query}':")
        for s in results:
            typer.echo(f"  - {s['id']} (Score: High)")
    else:
        typer.echo("❌ No matching skills found.")
