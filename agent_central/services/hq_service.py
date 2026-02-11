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

        self.skill_service = None
        self._skills_list_cache = None

    @property
    def _skill_service(self):
        if self.skill_service is None:
             from agent_central.services.skill_service import SkillService
             self.skill_service = SkillService(self.hq_path)
        return self.skill_service

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
        print(f"✅ Active Persona switched to: {role_name}")

    def list_roles(self):
        """Lists available roles in HQ."""
        roles_dir = self.hq_path / "roles"
        if not roles_dir.exists():
            return []
        return [f.stem for f in roles_dir.glob("*.md")]

    def list_skills(self):
        """Lists available skills in HQ."""
        if self._skills_list_cache is not None:
            return self._skills_list_cache

        skills_dir = self.hq_path / "skills"
        if not skills_dir.exists():
            return []

        result = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        self._skills_list_cache = result
        return result

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
            for t in tokens:
                if t in req_lower:
                    suggested_roles.append(role)
                    print(f"  🔍 [Proof] Inferred Role '{role}' from keyword '{t}'")
                    break
        
        # Check Skills (Smart Search)
        skill_service = self._skill_service
        
        # Aggregate all requirements into a single query string for semantic matching
        # (This is a simplified approach; ideally we'd extract key phrases)
        
        # 1. Direct Keyword Matching (Legacy + Precision)
        for skill in self.list_skills():
            tokens = get_tokens(skill)
            for t in tokens:
                if t in req_lower:
                    suggested_skills.append(skill)
                    print(f"  🔍 [Proof] Inferred Skill '{skill}' from keyword '{t}'")
                    break
        
        # 2. Semantic/Registry Matching (Expansion)
        # Only search if we have requirements text
        if requirements:
            semantic_matches = skill_service.search_skills(requirements, top_k=3)
            for skill_obj in semantic_matches:
                if skill_obj['id'] not in suggested_skills:
                   suggested_skills.append(skill_obj['id'])
                   print(f"  🧠 [Smart-Match] Inferred Skill '{skill_obj['id']}' from intent.")

        return list(set(suggested_roles)), list(set(suggested_skills))

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
            print("⚠️  No agents or skills listed/inferred.")
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

        print(f"✅ Hired {hired_roles} roles and {hired_skills} skills to {context_root}")
        
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
            
            print(f"⚠️  Logged {len(new_requests)} missing assets to {request_file}")
            print("👉 Run 'ai ops sync' (future) or contact HQ to fulfil these requests.")

    def learn_from_project(self, project_path: str = "."):
        """Extracts learned patterns from project and syncs to HQ."""
        project_root = Path(project_path).resolve()
        agents_file = project_root / "AGENTS.md"
        
        if not agents_file.exists():
            print(f"⚠️  No AGENTS.md found at {project_root}")
            return

        import re
        content = agents_file.read_text(encoding="utf-8")
        
        # Regex to find "## Learned" or "## <number>. Learned"
        pattern = r"##\s+(?:\d+\.\s*)?Learned"
        match = re.search(pattern, content)
        
        if not match:
            print("ℹ️  No '## Learned' section found in AGENTS.md.")
            return

        # Get text starting from the matched header
        start_index = match.end()
        text_after = content[start_index:]
        
        # Stop at next "## " header
        next_header_match = re.search(r"\n##\s+", text_after)
        if next_header_match:
            learned_content = text_after[:next_header_match.start()].strip()
        else:
            learned_content = text_after.strip()

        if not learned_content:
            print("ℹ️  '## Learned' section is empty.")
            return

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = project_root.name
        
        # Save to HQ Knowledge
        knowledge_file = self.hq_path / "knowledge" / "patterns" / f"learning_{project_name}_{timestamp}.md"
        knowledge_file.parent.mkdir(parents=True, exist_ok=True)
        
        knowledge_file.write_text(f"# Learning from {project_name}\n\n{learned_content}", encoding="utf-8")
        print(f"📢 Synced new knowledge to: {knowledge_file.name}")

    def consolidate_knowledge(self):
        """Processes raw knowledge and updates master roles/skills."""
        patterns_dir = self.hq_path / "knowledge" / "patterns"
        archive_dir = self.hq_path / "knowledge" / "archive" / "patterns"
        archive_dir.mkdir(parents=True, exist_ok=True)

        if not patterns_dir.exists():
            print("ℹ️  No knowledge patterns found to consolidate.")
            return

        knowledge_files = list(patterns_dir.glob("*.md"))
        if not knowledge_files:
            print("ℹ️  No new knowledge patterns to process.")
            return

        roles = self.list_roles()
        
        for k_file in knowledge_files:
            content = k_file.read_text(encoding="utf-8")
            # Determine target role based on simple keyword matching
            target_role = None
            content_lower = content.lower()
            
            if "architect" in content_lower or "design" in content_lower or "pattern" in content_lower:
                target_role = "architect"
            elif "qa" in content_lower or "test" in content_lower or "regression" in content_lower:
                target_role = "jules-qa"
            elif "backend" in content_lower or "api" in content_lower or "logic" in content_lower:
                target_role = "backend-dev"
            elif "frontend" in content_lower or "ui" in content_lower or "ux" in content_lower:
                target_role = "frontend-dev"
            else:
                target_role = "task-assigner" # Default to manager for generic patterns

            if target_role in roles:
                self._upskill_role(target_role, content)
                # Archive the processed file
                shutil.move(str(k_file), str(archive_dir / k_file.name))
                print(f"🚀 Upskilled '{target_role}' with knowledge from {k_file.name}")

    def _synthesize_wisdom(self, raw_text: str) -> str:
        """
        Simulates an LLM to structure raw text into a Protocol.
        Extracts 'Topic', 'Rule', and 'Type'.
        """
        import re
        
        # Heuristic extraction
        topic = "General Protocol"
        rule = raw_text
        
        # Try to find a topic in [Brackets] or first few words
        match = re.search(r"\[(.*?)\]", raw_text)
        if match:
            topic = match.group(1).title()
            # Remove the tag from the rule text for cleanliness
            rule = raw_text.replace(f"[{match.group(1)}]", "").strip()
        else:
            # First 3 words as topic
            words = raw_text.split()
            if len(words) > 3:
                topic = " ".join(words[:3]).title()

        # Determine Emoji/Type
        p_type = "🧠 Learned Protocol"
        if "fix" in topic.lower() or "bug" in topic.lower():
            p_type = "🛠️ Verification Protocol"
        elif "pattern" in topic.lower():
            p_type = "📐 Design Standard"

        # Format into the "Sauce"
        synthesized = f"""
### {p_type}: {topic}
> **Rule**: {rule}
> **Context**: Derived from project experience.
"""
        return synthesized

    def _upskill_role(self, role_name: str, knowledge_content: str):
        """Appends knowledge to a specific role's Learned Protocols section."""
        role_file = self.hq_path / "roles" / f"{role_name}.md"
        if not role_file.exists():
            return

        current_content = role_file.read_text(encoding="utf-8")
        
        # Extract new wisdom (skip header of knowledge file)
        raw_wisdom_lines = knowledge_content.split("\n\n", 1)[-1].strip().splitlines()
        
        # Synthesize each line (assuming bullet points)
        synthesized_block = ""
        for line in raw_wisdom_lines:
            if line.strip():
                clean_line = line.strip("- ").strip()
                s_wisdom = self._synthesize_wisdom(clean_line)
                synthesized_block += f"{s_wisdom}\n"
        
        if "## 7. Learned Protocols" in current_content:
            updated_content = current_content + "\n" + synthesized_block
        else:
            updated_content = current_content + "\n\n## 7. Learned Protocols\n" + synthesized_block
            
        role_file.write_text(updated_content, encoding="utf-8")
