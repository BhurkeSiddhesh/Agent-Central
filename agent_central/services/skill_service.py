import datetime
import json
from pathlib import Path
import yaml


class SkillService:
    def __init__(self, hq_path: Path):
        self.hq_path = hq_path
        self.skills_dir = self.hq_path / "skills"
        self.registry_file = self.skills_dir / "skills.index.json"
        self.legacy_registry_file = self.skills_dir / "skills.json"

        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skills directory not found at {self.skills_dir}")

    def build_registry(self):
        """Scans all skills and builds a JSON manifest."""
        registry = []
        print(f"🔍 Scanning skills in {self.skills_dir}...")

        # Iterate over immediate subdirectories
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_id = skill_path.name
                readme_path = skill_path / "README.md"
                skill_file_path = skill_path / "SKILL.md"

                # Heuristic: Read first few lines of README or SKILL.md for description
                description = "No description available."
                keywords = [skill_id.replace("-", " ")]  # Default keywords from ID

                metadata = {
                    "id": skill_id,
                    "name": skill_id.replace("-", " ").title(),
                    "description": description,
                    "version": "0.0.0",
                    "tags": [],
                    "domains": [],
                    "tech": [],
                    "role_affinity": [],
                    "provides": [],
                    "requires": [],
                    "conflicts": [],
                    "guardrail": False,
                    "risk_level": "low",
                    "last_updated": None,
                }

                content_source = None
                if skill_file_path.exists():
                    content_source = skill_file_path
                elif readme_path.exists():
                    content_source = readme_path

                if content_source:
                    try:
                        content = content_source.read_text(encoding="utf-8")
                        front_matter, body = self._extract_front_matter(content)

                        if front_matter:
                            for key in metadata:
                                if key in front_matter:
                                    metadata[key] = front_matter[key]
                            # Ensure registry ID aligns with folder name
                            metadata["id"] = skill_id
                            # Normalize list-like fields
                            for key in [
                                "tags",
                                "domains",
                                "tech",
                                "role_affinity",
                                "provides",
                                "requires",
                                "conflicts",
                            ]:
                                metadata[key] = self._ensure_list(metadata.get(key))

                        lines = [line.strip() for line in body.splitlines() if line.strip()]
                        # Extract description (first non-header line usually)
                        for line in lines:
                            if not line.startswith("#"):
                                description = (
                                    line[:200] + "..."
                                    if len(line) > 200
                                    else line
                                )
                                break

                        if metadata.get("description") in (None, "No description available."):
                            metadata["description"] = description

                        # Extract keywords/tags if present (e.g., Tags: python, backend)
                        # For now, we perform simple token extraction from the name and description
                        desc_tokens = set(description.lower().split())
                        # Filter for interesting words (simple stopword removal could happen here)
                        keywords.extend([w for w in desc_tokens if len(w) > 4])
                        keywords.extend([str(t) for t in metadata.get("tags", [])])
                        keywords.extend([str(t) for t in metadata.get("tech", [])])
                        keywords.extend([str(t) for t in metadata.get("domains", [])])
                        keywords.extend([str(t) for t in metadata.get("provides", [])])

                    except Exception as e:
                        print(f"⚠️  Error reading {skill_id}: {e}")

                normalized_metadata = self._normalize_dates(metadata)

                registry.append(
                    {
                        "id": normalized_metadata.get("id", skill_id),
                        "name": normalized_metadata.get(
                            "name", skill_id.replace("-", " ").title()
                        ),
                        "description": normalized_metadata.get("description", description),
                        "version": normalized_metadata.get("version", "0.0.0"),
                        "tags": normalized_metadata.get("tags", []),
                        "domains": normalized_metadata.get("domains", []),
                        "tech": normalized_metadata.get("tech", []),
                        "role_affinity": normalized_metadata.get("role_affinity", []),
                        "provides": normalized_metadata.get("provides", []),
                        "requires": normalized_metadata.get("requires", []),
                        "conflicts": normalized_metadata.get("conflicts", []),
                        "guardrail": normalized_metadata.get("guardrail", False),
                        "risk_level": normalized_metadata.get("risk_level", "low"),
                        "last_updated": normalized_metadata.get("last_updated"),
                        "keywords": list(set(keywords)),  # Deduplicate
                        "path": str(skill_path.relative_to(self.hq_path)),
                    }
                )

        # Save registry
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        print(f"✅ skills.index.json built with {len(registry)} skills.")
        return registry

    def load_registry(self):
        """Loads the registry from JSON."""
        if self.registry_file.exists():
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)

        if self.legacy_registry_file.exists():
            with open(self.legacy_registry_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return self.build_registry()

    def search_skills(self, query: str, top_k: int = 5):
        """
        Semantic-ish search for skills using keyword density.
        Returns top-k skills that match the query.
        """
        registry = self.load_registry()
        if not query:
            return registry[:top_k]  # Return random/first ones if no query

        scored_skills = []
        query_tokens = set(query.lower().split())

        for skill in registry:
            score = self._calculate_score(skill, query_tokens)
            if score > 0:
                scored_skills.append((score, skill))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[0], reverse=True)

        # Return just the skill objects
        return [s[1] for s in scored_skills[:top_k]]

    def _calculate_score(self, skill: dict, query_tokens: set) -> float:
        """Calculates a relevancy score for a skill against query tokens."""
        score = 0

        # Check ID/Name (High weight)
        skill_name_tokens = set(skill["name"].lower().split())
        name_match = len(query_tokens.intersection(skill_name_tokens))
        score += name_match * 10

        # Check Keywords (Medium weight)
        skill_keywords = set([k.lower() for k in skill["keywords"]])
        keyword_match = len(query_tokens.intersection(skill_keywords))
        score += keyword_match * 5

        # Check Description (Low weight)
        # Simple existence check
        desc_lower = skill["description"].lower()
        for token in query_tokens:
            if token in desc_lower:
                score += 1

        return score

    def _extract_front_matter(self, content: str):
        if not content.startswith("---"):
            return None, content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None, content
        _, fm_raw, body = parts
        try:
            fm = yaml.safe_load(fm_raw) or {}
        except Exception:
            fm = {}
        return fm, body.strip()

    def _ensure_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _normalize_dates(self, value):
        if isinstance(value, dict):
            return {k: self._normalize_dates(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._normalize_dates(v) for v in value]
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        return value
