import typer
from agent_central.commands import init, hire, ops

app = typer.Typer(
    name="ai-ops",
    help="AI-Ops CLI: Orchestrating the Agency",
    add_completion=False,
)

app.add_typer(init.app, name="init")
app.add_typer(hire.app, name="hire")
app.add_typer(ops.app, name="ops")

if __name__ == "__main__":
    app()
