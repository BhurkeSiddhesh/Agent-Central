import shutil
import os
from pathlib import Path
import yaml

class HQService:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        
        # Central HQ is located relative to this source file
        self.central_hq_path = Path(__file__).parent.parent.parent / "agency-hq"
        
        # Local HQ is an optional override in the project
        self.local_hq_path = self.project_root / ".agency-hq"
        
        # Determine which HQ to use (prefer local if exists, else central)
        if self.local_hq_path.exists():
            self.hq_path = self.local_hq_path
        else:
            self.hq_path = self.central_hq_path

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

    def get_skill_content(self, skill_name: str) -> str:
        """Retrieves content for a given skill."""
        skill_file = self.hq_path / "skills" / skill_name / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"Skill {skill_name} not found in HQ.")
        return skill_file.read_text(encoding="utf-8")

    def set_active_persona(self, role_name: str):
        """Sets the ACTIVE_PERSONA.md to the specified role."""
        content = self.get_role_content(role_name)
        self.active_persona_file.parent.mkdir(parents=True, exist_ok=True)
        self.active_persona_file.write_text(content, encoding="utf-8")
        print(f"âœ… Active Persona switched to: {role_name}")

    def list_roles(self):
        """Lists available roles in HQ."""
        roles_dir = self.hq_path / "roles"
        if not roles_dir.exists():
            return []
        return [f.stem for f in roles_dir.glob("*.md")]

    def list_skills(self):
        """Lists available skills in HQ."""
        skills_dir = self.hq_path / "skills"
        if not skills_dir.exists():
            return []
        return [d.name for d in skills_dir.iterdir() if d.is_dir()]

    def infer_assets(self, requirements: str):
        """Token-based inference for roles and skills."""
        if not requirements:
            return [], []
        
        req_lower = requirements.lower()
        suggested_roles = []
        suggested_skills = []

        def get_tokens(name):
            return [w for w in name.lower().replace("-", " ").split() if len(w) >= 2]

        # Check Roles
        for role in self.list_roles():
            tokens = get_tokens(role)
            if any(t in req_lower for t in tokens):
                suggested_roles.append(role)
        
        # Check Skills
        for skill in self.list_skills():
            tokens = get_tokens(skill)
            if any(t in req_lower for t in tokens):
                suggested_skills.append(skill)
        
        return suggested_roles, suggested_skills

    def hire_from_config(self, config_path: str):
        """Hires agents and skills based on a configuration file."""
        config_file = Path(config_path).resolve()
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_file}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse agency config: {e}")

        project_requirements = config.get("project_requirements", "")
        required_agents_raw = config.get("required_agents", [])
        required_skills_raw = config.get("required_skills", [])
        
        required_agents = set()
        required_skills = set()

        # Helper to extract and infer from mixed list
        def process_raw_list(raw_list, is_role=True):
            names = set()
            for item in raw_list:
                if isinstance(item, str):
                    names.add(item)
                    # Also infer from the string itself in case it's a descriptive name
                    inf_r, inf_s = self.infer_assets(item)
                    required_agents.update(inf_r)
                    required_skills.update(inf_s)
                elif isinstance(item, dict):
                    # Use 'role'/'skill' key as the primary name if it exists
                    val = item.get("role") if is_role else item.get("skill")
                    val = val or item.get("name")
                    if val:
                        names.add(val)
                    # Infer from the entire dictionary content (description, etc.)
                    inf_r, inf_s = self.infer_assets(str(item))
                    required_agents.update(inf_r)
                    required_skills.update(inf_s)
            return names

        required_agents.update(process_raw_list(required_agents_raw, is_role=True))
        required_skills.update(process_raw_list(required_skills_raw, is_role=False))

        # Perform Global Inference
        if project_requirements:
            inf_roles, inf_skills = self.infer_assets(project_requirements)
            required_agents.update(inf_roles)
            required_skills.update(inf_skills)


        if not required_agents and not required_skills:
            print("âš ï¸  No agents or skills listed/inferred.")
            return

        context_root = config_file.parent / ".ai-context"
        team_dir = context_root / "team"
        skills_dir = context_root / "skills"
        
        team_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        missing_assets = []
        hired_roles = 0
        hired_skills = 0

        # Hire Roles
        for agent in required_agents:
            try:
                content = self.get_role_content(agent)
                (team_dir / f"{agent}.md").write_text(content, encoding="utf-8")
                hired_roles += 1
            except ValueError:
                missing_assets.append(f"role:{agent}")

        # Hire Skills
        for skill in required_skills:
            try:
                content = self.get_skill_content(skill)
                # Create skill directory in destination
                (skills_dir / skill).mkdir(exist_ok=True)
                (skills_dir / skill / "SKILL.md").write_text(content, encoding="utf-8")
                hired_skills += 1
            except ValueError:
                missing_assets.append(f"skill:{skill}")

        print(f"âœ… Hired {hired_roles} roles and {hired_skills} skills to {context_root}")
        
        if missing_assets:
            self._log_missing_agents(missing_assets, context_root)
            
    def _log_missing_agents(self, assets: list, context_path: Path = None):
        """Logs missing assets to HQ_REQUESTS.md"""
        target_path = context_path if context_path else self.context_path
        request_file = target_path / "HQ_REQUESTS.md"
        request_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing requests to avoid duplicates
        existing_requests = set()
        if request_file.exists():
            lines = request_file.read_text().splitlines()
            existing_requests = {line.strip("- ").strip() for line in lines if line.strip().startswith("-")}

        new_requests = [a for a in assets if a not in existing_requests]
        
        if new_requests:
            with open(request_file, "a") as f:
                if not request_file.exists() or request_file.stat().st_size == 0:
                    f.write("# HQ Asset Requests\n\n")
                for asset in new_requests:
                    f.write(f"- {asset}\n")
            
            print(f"âš ï¸  Logged {len(new_requests)} missing assets to {request_file}")
            print("ðŸ‘‰ Run 'ai ops sync' (future) or contact HQ to fulfil these requests.")
