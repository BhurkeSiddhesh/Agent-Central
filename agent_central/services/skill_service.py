import json
from pathlib import Path
import os

class SkillService:
    def __init__(self, hq_path: Path):
        self.hq_path = hq_path
        self.skills_dir = self.hq_path / "skills"
        self.registry_file = self.skills_dir / "skills.json"
        self._registry_cache = None
        self._index = None
        
        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skills directory not found at {self.skills_dir}")

    def build_registry(self):
        """Scans all skills and builds a JSON manifest."""
        registry = []
        print(f"🔄 Scanning skills in {self.skills_dir}...")
        
        # Iterate over immediate subdirectories
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_id = skill_path.name
                readme_path = skill_path / "README.md"
                skill_file_path = skill_path / "SKILL.md"
                
                # Heuristic: Read first few lines of README or SKILL.md for description
                description = "No description available."
                keywords = [skill_id.replace("-", " ")] # Default keywords from ID
                
                content_source = None
                if readme_path.exists():
                    content_source = readme_path
                elif skill_file_path.exists():
                    content_source = skill_file_path
                
                if content_source:
                    try:
                        content = content_source.read_text(encoding="utf-8")
                        lines = [l.strip() for l in content.splitlines() if l.strip()]
                        # Extract description (first non-header line usually)
                        for line in lines:
                            if not line.startswith("#"):
                                description = line[:200] + "..." if len(line) > 200 else line
                                break
                        
                        # Extract keywords/tags if present (e.g., Tags: python, backend)
                        # For now, we perform simple token extraction from the name and description
                        desc_tokens = set(description.lower().split())
                        # Filter for interesting words (simple stopword removal could happen here)
                        keywords.extend([w for w in desc_tokens if len(w) > 4])
                        
                    except Exception as e:
                        print(f"⚠️  Error reading {skill_id}: {e}")

                registry.append({
                    "id": skill_id,
                    "name": skill_id.replace("-", " ").title(),
                    "description": description,
                    "keywords": list(set(keywords)), # Deduplicate
                    "path": str(skill_path.relative_to(self.hq_path))
                })
        
        # Save registry
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
            
        print(f"✅ skills.json built with {len(registry)} skills.")
        return registry

    def load_registry(self):
        """Loads the registry from JSON."""
        if self._registry_cache:
            return self._registry_cache

        if not self.registry_file.exists():
            return self.build_registry()
        
        with open(self.registry_file, "r", encoding="utf-8") as f:
            self._registry_cache = json.load(f)
            return self._registry_cache

    def _build_index(self, registry):
        """Builds an inverted index for faster search."""
        index = {} # token -> set of skill indices

        for idx, skill in enumerate(registry):
            # Index Name
            name_tokens = skill['name'].lower().split()
            for token in name_tokens:
                if token not in index: index[token] = set()
                index[token].add(idx)

            # Index Keywords
            for kw in skill['keywords']:
                kw_tokens = kw.lower().split()
                for token in kw_tokens:
                    if token not in index: index[token] = set()
                    index[token].add(idx)

            # Index Description (words)
            desc_tokens = skill['description'].lower().split()
            for token in desc_tokens:
                if token not in index: index[token] = set()
                index[token].add(idx)

        self._index = index

    def search_skills(self, query: str, top_k: int = 5):
        """
        Semantic-ish search for skills using keyword density.
        Returns top-k skills that match the query.
        """
        registry = self.load_registry()
        if not query:
            return registry[:top_k] # Return random/first ones if no query
            
        if self._index is None:
            self._build_index(registry)

        scored_skills = []
        query_tokens = set(query.lower().split())
        candidate_indices = set()
        
        # Use inverted index to find candidates
        # 1. Exact matches and Substring matches (simulated via vocabulary scan)
        vocab_keys = self._index.keys()

        for q_token in query_tokens:
            # Check all indexed tokens to see if they contain the query token
            # This handles both exact matches (q_token == vocab_token)
            # and substring matches (q_token in vocab_token)
            for vocab_token in vocab_keys:
                if q_token in vocab_token:
                    candidate_indices.update(self._index[vocab_token])

        for idx in sorted(candidate_indices):
            skill = registry[idx]
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
        skill_name_tokens = set(skill['name'].lower().split())
        name_match = len(query_tokens.intersection(skill_name_tokens))
        score += name_match * 10
        
        # Check Keywords (Medium weight)
        skill_keywords = set([k.lower() for k in skill['keywords']])
        keyword_match = len(query_tokens.intersection(skill_keywords))
        score += keyword_match * 5
        
        # Check Description (Low weight)
        # Simple existence check
        desc_lower = skill['description'].lower()
        for token in query_tokens:
            if token in desc_lower:
                score += 1
                
        return score
