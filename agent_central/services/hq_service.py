import datetime
import hashlib
import json
import shutil
from pathlib import Path
from typing import List

import yaml

from agent_central.models.agency_config import AgencyConfig
from agent_central.services.profile_service import ProfileService
from agent_central.services.selection_service import SelectionService
from agent_central.services.skill_service import SkillService


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
        print(f"✅ Active Persona switched to: {role_name}")

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
            for t in tokens:
                if t in req_lower:
                    suggested_roles.append(role)
                    print(f"  🔍 [Proof] Inferred Role '{role}' from keyword '{t}'")
                    break

        # Check Skills (Smart Search)
        skill_service = SkillService(self.hq_path)

        # 1. Direct Keyword Matching (Legacy + Precision)
        for skill in self.list_skills():
            tokens = get_tokens(skill)
            for t in tokens:
                if t in req_lower:
                    suggested_skills.append(skill)
                    print(f"  🔍 [Proof] Inferred Skill '{skill}' from keyword '{t}'")
                    break

        # 2. Semantic/Registry Matching (Expansion)
        if requirements:
            semantic_matches = skill_service.search_skills(requirements, top_k=3)
            for skill_obj in semantic_matches:
                if skill_obj["id"] not in suggested_skills:
                    suggested_skills.append(skill_obj["id"])
                    print(
                        f"  🧠 [Smart-Match] Inferred Skill '{skill_obj['id']}' from intent."
                    )

        return list(set(suggested_roles)), list(set(suggested_skills))

    def hire_from_config(self, config_path: str):
        """Hires agents and skills based on a configuration file."""
        config_file = Path(config_path).resolve()
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_file}")

        config = self._load_config(config_file)

        project_requirements = (
            config.project_requirements or config.requirements.functional or ""
        )
        required_agents_raw = config.required_agents or []

        required_agents = set()

        # Helper to extract and infer from mixed list
        def process_raw_list(raw_list) -> set:
            names = set()
            for item in raw_list:
                if isinstance(item, str):
                    names.add(item)
                    # Also infer from the string itself in case it's a descriptive name
                    inf_r, _ = self.infer_assets(item)
                    required_agents.update(inf_r)
                elif isinstance(item, dict):
                    val = item.get("role") or item.get("name")
                    if val:
                        names.add(val)
                    # Infer from the entire dictionary content (description, etc.)
                    inf_r, _ = self.infer_assets(str(item))
                    required_agents.update(inf_r)
            return names

        required_agents.update(process_raw_list(required_agents_raw))

        # Role policy overrides
        required_agents.update(config.role_policy.required_roles)
        required_agents.update(config.role_policy.optional_roles)

        # [POLICY] Always include the Task Assigner (Manager)
        required_agents.add("task-assigner")

        # Perform Global Inference
        if project_requirements:
            inf_roles, _ = self.infer_assets(project_requirements)
            required_agents.update(inf_roles)

        context_root = config_file.parent / ".ai-context"
        team_dir = context_root / "team"
        skills_dir = context_root / "skills"

        team_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        missing_assets = []
        hired_roles = 0
        hired_skills = 0

        # Build profile + skill selection
        selector = SelectionService(self.hq_path, config_file.parent)
        selection = selector.suggest_skills(config)

        # Write profile, manifest, lock
        profile_service = ProfileService(config_file.parent)
        profile_service.write_profile(selection["profile"], context_root)
        selector.write_manifest(selection["manifest"], context_root)
        selector.write_lock(selection["selected"], selection["scored"], context_root)

        # Hire Roles
        for agent in required_agents:
            try:
                content = self.get_role_content(agent)
                (team_dir / f"{agent}.md").write_text(content, encoding="utf-8")
                hired_roles += 1
            except ValueError:
                missing_assets.append(f"role:{agent}")

        # Hire Skills
        for skill in selection["selected"]:
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

    def record_skill_feedback(self, skill_id: str, result: str, note: str = ""):
        """Record feedback for a skill selection."""
        learning_dir = self.context_path / "learning"
        learning_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "project": self.project_root.name,
            "skill_id": skill_id,
            "result": result,
            "note": note,
        }
        context_hash = hashlib.sha256(
            f"{payload['project']}|{skill_id}|{result}|{note}".encode("utf-8")
        ).hexdigest()[:12]
        payload["context_hash"] = context_hash

        events_file = learning_dir / "events.jsonl"
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        print(f"📝 Recorded feedback for skill '{skill_id}'")

    def _log_missing_agents(self, assets: list, context_path: Path = None):
        """Logs missing assets to HQ_REQUESTS.md"""
        target_path = context_path if context_path else self.context_path
        request_file = target_path / "HQ_REQUESTS.md"
        request_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing requests to avoid duplicates
        existing_requests = set()
        if request_file.exists():
            lines = request_file.read_text().splitlines()
            existing_requests = {
                line.strip("- ").strip()
                for line in lines
                if line.strip().startswith("-")
            }

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

        learned_content = ""
        if agents_file.exists():
            import re

            content = agents_file.read_text(encoding="utf-8")

            # Regex to find "## Learned" or "## <number>. Learned"
            pattern = r"##\s+(?:\d+\.\s*)?Learned"
            match = re.search(pattern, content)

            if match:
                # Get text starting from the matched header
                start_index = match.end()
                text_after = content[start_index:]

                # Stop at next "## " header
                next_header_match = re.search(r"\n##\s+", text_after)
                if next_header_match:
                    learned_content = text_after[: next_header_match.start()].strip()
                else:
                    learned_content = text_after.strip()
            else:
                print("ℹ️  No '## Learned' section found in AGENTS.md.")
        else:
            print(f"⚠️  No AGENTS.md found at {project_root}")

        feedback_lines = self._collect_skill_feedback(project_root)
        if feedback_lines:
            if learned_content:
                learned_content += "\n\n## Skill Feedback\n"
            else:
                learned_content = "## Skill Feedback\n"
            learned_content += "\n".join(feedback_lines)

        if not learned_content.strip():
            print("ℹ️  No learnings or feedback found to sync.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = project_root.name

        # Save to HQ Knowledge
        knowledge_file = (
            self.hq_path
            / "knowledge"
            / "patterns"
            / f"learning_{project_name}_{timestamp}.md"
        )
        knowledge_file.parent.mkdir(parents=True, exist_ok=True)

        knowledge_file.write_text(
            f"# Learning from {project_name}\n\n{learned_content}",
            encoding="utf-8",
        )
        print(f"📢 Synced new knowledge to: {knowledge_file.name}")

    def consolidate_knowledge(self):
        """Processes raw knowledge and updates master roles/skills."""
        self._update_skill_quality()

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

            if (
                "architect" in content_lower
                or "design" in content_lower
                or "pattern" in content_lower
            ):
                target_role = "architect"
            elif (
                "qa" in content_lower
                or "test" in content_lower
                or "regression" in content_lower
            ):
                target_role = "jules-qa"
            elif "backend" in content_lower or "api" in content_lower or "logic" in content_lower:
                target_role = "backend-dev"
            elif (
                "frontend" in content_lower
                or "ui" in content_lower
                or "ux" in content_lower
            ):
                target_role = "frontend-dev"
            else:
                target_role = "task-assigner"  # Default to manager for generic patterns

            if target_role in roles:
                self._upskill_role(target_role, content)
                # Archive the processed file
                shutil.move(str(k_file), str(archive_dir / k_file.name))
                print(f"🚀 Upskilled '{target_role}' with knowledge from {k_file.name}")

    def _collect_skill_feedback(self, project_root: Path) -> List[str]:
        """Collects skill feedback events and writes them to HQ logs."""
        events_file = project_root / ".ai-context" / "learning" / "events.jsonl"
        if not events_file.exists():
            return []

        events_index_file = self.hq_path / "knowledge" / "events_index.json"
        seen = set()
        if events_index_file.exists():
            try:
                seen = set(json.loads(events_index_file.read_text(encoding="utf-8")))
            except Exception:
                seen = set()

        feedback_log = self.hq_path / "knowledge" / "skill_feedback.jsonl"
        feedback_lines = []
        new_hashes = []

        with open(events_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                context_hash = event.get("context_hash")
                if not context_hash or context_hash in seen:
                    continue

                seen.add(context_hash)
                new_hashes.append(context_hash)
                result = event.get("result", "neutral")
                skill_id = event.get("skill_id", "unknown")
                note = event.get("note", "")
                if note:
                    feedback_lines.append(
                        f"- [SkillFeedback][{result}] {skill_id}: {note}"
                    )
                else:
                    feedback_lines.append(f"- [SkillFeedback][{result}] {skill_id}")

                feedback_log.parent.mkdir(parents=True, exist_ok=True)
                with open(feedback_log, "a", encoding="utf-8") as logf:
                    logf.write(json.dumps(event) + "\n")

        if new_hashes:
            events_index_file.parent.mkdir(parents=True, exist_ok=True)
            events_index_file.write_text(
                json.dumps(sorted(seen), indent=2), encoding="utf-8"
            )

        return feedback_lines

    def _update_skill_quality(self):
        feedback_log = self.hq_path / "knowledge" / "skill_feedback.jsonl"
        if not feedback_log.exists():
            return

        quality_file = self.hq_path / "knowledge" / "skill_quality.json"
        quality = {"updated_at": None, "skills": {}}
        if quality_file.exists():
            try:
                quality = json.loads(quality_file.read_text(encoding="utf-8"))
            except Exception:
                quality = {"updated_at": None, "skills": {}}

        skills = quality.get("skills", {})
        events = feedback_log.read_text(encoding="utf-8").splitlines()
        if not events:
            return

        for line in events:
            try:
                event = json.loads(line)
            except Exception:
                continue
            skill_id = event.get("skill_id")
            if not skill_id:
                continue
            result = event.get("result", "neutral")

            entry = skills.get(skill_id, {"use_count": 0, "helpful_count": 0, "harmful_count": 0})
            entry["use_count"] += 1
            if result == "helpful":
                entry["helpful_count"] += 1
            elif result == "harmful":
                entry["harmful_count"] += 1
            skills[skill_id] = entry

        quality["skills"] = skills
        quality["updated_at"] = datetime.datetime.utcnow().isoformat()
        quality_file.parent.mkdir(parents=True, exist_ok=True)
        quality_file.write_text(json.dumps(quality, indent=2), encoding="utf-8")

        # Archive processed feedback
        archive_dir = self.hq_path / "knowledge" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archived = archive_dir / f"skill_feedback_{stamp}.jsonl"
        shutil.move(str(feedback_log), str(archived))

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
            if not line.strip() or line.strip().startswith("#"):
                continue
            clean_line = line.strip("- ").strip()
            s_wisdom = self._synthesize_wisdom(clean_line)
            synthesized_block += f"{s_wisdom}\n"

        if "## 7. Learned Protocols" in current_content:
            updated_content = current_content + "\n" + synthesized_block
        else:
            updated_content = (
                current_content + "\n\n## 7. Learned Protocols\n" + synthesized_block
            )

        role_file.write_text(updated_content, encoding="utf-8")

    def _load_config(self, config_file: Path) -> AgencyConfig:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Failed to parse agency config: {e}")
        return AgencyConfig.model_validate(raw)
