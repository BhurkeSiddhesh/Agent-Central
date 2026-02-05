import json
from pathlib import Path
import yaml


class SkillService:
    def __init__(self, hq_path: Path):
        """
        Initialize the SkillService for a given HQ installation path and prepare paths for skill registries.
        
        Parameters:
            hq_path (Path): Base HQ directory used to locate the skills folder.
        
        Raises:
            FileNotFoundError: If the skills directory (hq_path / "skills") does not exist.
        """
        self.hq_path = hq_path
        self.skills_dir = self.hq_path / "skills"
        self.registry_file = self.skills_dir / "skills.index.json"
        self.legacy_registry_file = self.skills_dir / "skills.json"

        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skills directory not found at {self.skills_dir}")

    def build_registry(self):
        """
        Builds a registry of skills by scanning the skills directory and writing a JSON index.
        
        Scans each immediate subdirectory of the service's skills directory, reads SKILL.md (preferred) or README.md, extracts optional YAML front matter and body, and assembles a registry entry for each skill. Normalizes list-like metadata fields, derives a short description from the first non-header line of the body when missing, collects and deduplicates keyword tokens, and writes the resulting list to the configured registry file.
        
        Returns:
            list[dict]: A list of registry entries. Each entry contains:
                - id (str)
                - name (str)
                - description (str)
                - version (str)
                - tags (list)
                - domains (list)
                - tech (list)
                - role_affinity (list)
                - provides (list)
                - requires (list)
                - conflicts (list)
                - guardrail (bool)
                - risk_level (str)
                - last_updated (optional)
                - keywords (list)
                - path (str): relative path to the skill folder from the HQ root
        """
        registry = []
        print(f"ðŸ”„ Scanning skills in {self.skills_dir}...")

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

                        lines = [l.strip() for l in body.splitlines() if l.strip()]
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
                        print(f"âš ï¸  Error reading {skill_id}: {e}")

                registry.append(
                    {
                        "id": metadata.get("id", skill_id),
                        "name": metadata.get(
                            "name", skill_id.replace("-", " ").title()
                        ),
                        "description": metadata.get("description", description),
                        "version": metadata.get("version", "0.0.0"),
                        "tags": metadata.get("tags", []),
                        "domains": metadata.get("domains", []),
                        "tech": metadata.get("tech", []),
                        "role_affinity": metadata.get("role_affinity", []),
                        "provides": metadata.get("provides", []),
                        "requires": metadata.get("requires", []),
                        "conflicts": metadata.get("conflicts", []),
                        "guardrail": metadata.get("guardrail", False),
                        "risk_level": metadata.get("risk_level", "low"),
                        "last_updated": metadata.get("last_updated"),
                        "keywords": list(set(keywords)),  # Deduplicate
                        "path": str(skill_path.relative_to(self.hq_path)),
                    }
                )

        # Save registry
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        print(f"âœ… skills.index.json built with {len(registry)} skills.")
        return registry

    def load_registry(self):
        """
        Load the skills registry from disk, falling back to the legacy registry file or rebuilding it by scanning the skills directory if no registry file exists.
        
        Returns:
            list[dict]: The registry as a list of skill metadata objects loaded from `skills.index.json`, `skills.json`, or generated by scanning the skills directory.
        """
        if self.registry_file.exists():
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)

        if self.legacy_registry_file.exists():
            with open(self.legacy_registry_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return self.build_registry()

    def search_skills(self, query: str, top_k: int = 5):
        """
        Finds and ranks skills that match a textual query using a keyword-density scoring heuristic.
        
        Parameters:
        	query (str): Text query used to match skills; tokenized on whitespace and lower-cased.
        	top_k (int): Maximum number of skill entries to return.
        
        Returns:
        	list[dict]: Ranked list of skill registry entries matching the query. If `query` is empty or falsy, returns the first `top_k` entries from the registry.
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
        """
        Compute a relevancy score for a skill given a set of query tokens.
        
        The score favors matches in the skill's name (highest weight), matches in its keywords (medium weight), and occurrences in its description (lowest weight).
        
        Parameters:
            skill (dict): Skill metadata containing at least "name", "keywords", and "description".
            query_tokens (set): Lowercased tokens from the query to match against the skill.
        
        Returns:
            float: Relevancy score where higher values indicate a stronger match between the skill and the query tokens.
        """
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
        """
        Extract YAML front matter from a text document and return the parsed front matter and the remaining body.
        
        Parameters:
        	content (str): The full text to inspect; expected to use '---' delimiters for YAML front matter.
        
        Returns:
        	tuple: A pair (fm, body) where `fm` is a dict of parsed YAML front matter or `None` if no valid front matter is present, and `body` is the remaining text with surrounding whitespace removed.
        """
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
        """
        Normalize a value into a list.
        
        Parameters:
            value: The input value which may be None, a list, or a single item.
        
        Returns:
            A list: an empty list if `value` is None, `value` unchanged if it is already a list, or a single-element list containing `value` otherwise.
        """
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]