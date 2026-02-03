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
