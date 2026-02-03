import shutil
import os
from pathlib import Path
import yaml

class HQService:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.hq_path = self.project_root / ".agency-hq"
        self.context_path = self.project_root / ".ai-context"
        self.active_persona_file = self.context_path / "ACTIVE_PERSONA.md"

    def setup_hq(self, source_hq_path: str):
        """Copies the HQ template to the project."""
        source = Path(source_hq_path).resolve()
        if not source.exists():
            raise FileNotFoundError(f"HQ Source not found at {source}")
        
        # In a real scenario, we might clone a git repo here.
        # For now, we copy from the local 'agency-hq' folder if it exists, or the source provided.
        if self.hq_path.exists():
            shutil.rmtree(self.hq_path)
        shutil.copytree(source, self.hq_path)
        
        # Create .ai-context structure
        self.context_path.mkdir(exist_ok=True)
        (self.context_path / "SQUAD_GOAL.md").touch()
        (self.context_path / "QA_REPORT.md").touch()

    def get_role_content(self, role_name: str) -> str:
        """Retrieves content for a given role."""
        role_file = self.hq_path / "roles" / f"{role_name}.md"
        if not role_file.exists():
            raise ValueError(f"Role {role_name} not found in HQ.")
        return role_file.read_text(encoding="utf-8")

    def set_active_persona(self, role_name: str):
        """Sets the ACTIVE_PERSONA.md to the specified role."""
        content = self.get_role_content(role_name)
        self.active_persona_file.parent.mkdir(parents=True, exist_ok=True)
        self.active_persona_file.write_text(content, encoding="utf-8")
        print(f"✅ Active Persona switched to: {role_name}")

    def list_roles(self):
        """Lists available roles in HQ."""
        roles_dir = self.hq_path / "roles"
        if not roles_dir.exists():
            return []
        return [f.stem for f in roles_dir.glob("*.md")]

    def hire_from_config(self, config_path: str):
        """Hires agents based on a configuration file."""
        config_file = Path(config_path).resolve()
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_file}")

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse agency config: {e}")

        required_agents = config.get("required_agents", [])
        if not required_agents:
            print("⚠️  No agents listed in 'required_agents'.")
            return

        team_dir = self.context_path / "team"
        team_dir.mkdir(parents=True, exist_ok=True)
        
        missing_agents = []
        hired_count = 0

        for agent in required_agents:
            try:
                content = self.get_role_content(agent)
                (team_dir / f"{agent}.md").write_text(content, encoding="utf-8")
                hired_count += 1
                # If this is the first agent, make them active by default
                if hired_count == 1:
                    self.set_active_persona(agent)
            except ValueError:
                missing_agents.append(agent)

        print(f"✅ Hired {hired_count} agents to {team_dir}")
        
        if missing_agents:
            self._log_missing_agents(missing_agents)
            
    def _log_missing_agents(self, agents: list):
        """Logs missing agents to HQ_REQUESTS.md"""
        request_file = self.context_path / "HQ_REQUESTS.md"
        
        # Read existing requests to avoid duplicates
        existing_requests = set()
        if request_file.exists():
            lines = request_file.read_text().splitlines()
            existing_requests = {line.strip("- ").strip() for line in lines if line.strip().startswith("-")}

        new_requests = [a for a in agents if a not in existing_requests]
        
        if new_requests:
            with open(request_file, "a") as f:
                if request_file.stat().st_size == 0:
                    f.write("# HQ Agent Requests\n\n")
                for agent in new_requests:
                    f.write(f"- {agent}\n")
            
            print(f"⚠️  Logged {len(new_requests)} missing agents to {request_file}")
            print("👉 Run 'ai ops sync' (future) or contact HQ to fulfil these requests.")

