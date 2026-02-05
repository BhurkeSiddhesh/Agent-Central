from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agent_central.models.agency_config import AgencyConfig
from agent_central.services.embedding_service import EmbeddingService
from agent_central.services.profile_service import ProfileService
from agent_central.services.skill_service import SkillService


def _tokenize(text: str) -> List[str]:
    """
    Split input text into lowercase alphanumeric tokens and exclude tokens shorter than three characters.
    
    Parameters:
        text (str): Input text to tokenize.
    
    Returns:
        List[str]: Lowercased tokens composed of alphanumeric characters with length >= 3. Returns an empty list if `text` is falsy.
    """
    if not text:
        return []
    tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) >= 3]


def _safe_set(values: List[str]) -> set:
    """
    Normalize a list of strings into a set of unique, trimmed, lowercase values.
    
    Parameters:
        values (List[str]): Iterable of strings; entries that are None, empty, or whitespace-only are ignored.
    
    Returns:
        set: A set of normalized strings (trimmed and lowercased).
    """
    return {v.strip().lower() for v in values if v and v.strip()}


class SelectionService:
    def __init__(self, hq_path: Path, project_root: Path):
        """
        Initialize the SelectionService with repository and project paths and set up dependent services.
        
        Parameters:
            hq_path (Path): Path to the HQ repository used to locate skill registry, embeddings, and knowledge data.
            project_root (Path): Path to the project workspace where manifests and locks will be written.
        """
        self.hq_path = Path(hq_path)
        self.project_root = Path(project_root)
        self.skill_service = SkillService(self.hq_path)
        self.embedding_service = EmbeddingService(self.hq_path)

    def suggest_skills(self, config: AgencyConfig) -> Dict:
        """
        Suggests and selects a set of skills for the given agency configuration.
        
        Constructs a query and profile from the provided config, scores all skills in the registry using embedding, keyword, and role-affinity signals (plus policy and quality adjustments), enforces required/includes/guardrails and prerequisites, resolves conflicts and exclusions, applies an optional max-skills budget, and builds a final manifest.
        
        Parameters:
            config (AgencyConfig): Configuration object describing project requirements, role policy, and skill policy used to drive query construction and selection rules.
        
        Returns:
            result (dict): A dictionary containing:
                - profile: The generated profile snapshot used for scoring.
                - selected: A sorted list of selected skill IDs.
                - manifest: A manifest dict summarizing selected skills, their scores, reasons, exclusions, and policy context.
                - scored: A mapping of skill ID to metadata including `score`, `reasons`, and the original `skill` entry.
        """
        registry = self.skill_service.load_registry()
        profile_service = ProfileService(self.project_root)
        profile = profile_service.build_profile(config)

        query_text = self._build_query_text(config, profile)
        query_tokens = set(_tokenize(query_text))

        # Optional embeddings
        skill_vectors = self.embedding_service.load_or_build(registry)
        query_vector = (
            self.embedding_service.embed_query(query_text) if skill_vectors else None
        )

        role_tokens = _safe_set(
            config.role_policy.required_roles
            + config.role_policy.optional_roles
            + self._extract_names(config.required_agents)
        )

        required_skill_ids = _safe_set(self._extract_names(config.required_skills))
        policy = config.skill_policy

        guardrails = _safe_set(
            policy.guardrail_skills
            or ["security-basics", "testing-basics", "code-review-checklist"]
        )

        inferred = {
            s["id"]
            for s in self.skill_service.search_skills(query_text, top_k=5)
        }

        include_skills = _safe_set(policy.include_skills)
        exclude_skills = _safe_set(policy.exclude_skills)

        initial_set = set(required_skill_ids) | guardrails | inferred | include_skills

        quality = self._load_skill_quality()

        scored: Dict[str, Dict] = {}
        for skill in registry:
            score, reasons = self._score_skill(
                skill,
                query_tokens,
                role_tokens,
                profile,
                skill_vectors,
                query_vector,
                policy,
                guardrails,
                quality,
            )
            scored[skill["id"]] = {
                "score": score,
                "reasons": reasons,
                "skill": skill,
            }

        selected = set()
        for skill_id, meta in scored.items():
            if skill_id in initial_set or meta["score"] >= policy.min_score:
                selected.add(skill_id)

        # Ensure explicitly required/included skills are present even if missing from registry
        for missing_id in required_skill_ids | include_skills:
            if missing_id not in scored:
                scored[missing_id] = {
                    "score": policy.min_score,
                    "reasons": ["missing_registry"],
                    "skill": {
                        "id": missing_id,
                        "name": missing_id,
                        "description": "",
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
                        "keywords": [],
                    },
                }
                selected.add(missing_id)

        # Enforce prerequisites
        for skill_id in list(selected):
            requires = scored[skill_id]["skill"].get("requires", [])
            for req in requires:
                if req not in scored:
                    continue
                selected.add(req)
                scored[req]["reasons"].append(f"required_by:{skill_id}")

        # Apply excludes
        selected = {s for s in selected if s not in exclude_skills}

        # Resolve conflicts
        excluded = []
        for skill_id in list(selected):
            conflicts = scored[skill_id]["skill"].get("conflicts", [])
            for conflict in conflicts:
                if conflict in selected:
                    left = scored[skill_id]
                    right = scored[conflict]
                    # Keep higher score unless explicit required/guardrail/include
                    protected = (
                        conflict in required_skill_ids
                        or conflict in guardrails
                        or conflict in include_skills
                    )
                    if protected:
                        selected.discard(skill_id)
                        excluded.append(
                            {
                                "id": skill_id,
                                "reason": f"conflicts_with:{conflict}",
                            }
                        )
                    else:
                        if right["score"] >= left["score"]:
                            selected.discard(skill_id)
                            excluded.append(
                                {
                                    "id": skill_id,
                                    "reason": f"conflicts_with:{conflict}",
                                }
                            )
                        else:
                            selected.discard(conflict)
                            excluded.append(
                                {
                                    "id": conflict,
                                    "reason": f"conflicts_with:{skill_id}",
                                }
                            )

        # Apply max_skills budget (do not drop protected)
        protected = required_skill_ids | guardrails | include_skills
        if policy.max_skills and len(selected) > policy.max_skills:
            selected = self._apply_budget(
                selected, scored, protected, profile, policy.max_skills
            )

        manifest = self._build_manifest(
            config,
            selected,
            scored,
            profile,
            required_skill_ids,
            guardrails,
            include_skills,
            inferred,
            excluded,
            policy,
        )

        return {
            "profile": profile,
            "selected": sorted(selected),
            "manifest": manifest,
            "scored": scored,
        }

    def write_manifest(self, manifest: Dict, context_root: Path) -> Path:
        """
        Write the provided manifest as a pretty-printed JSON file named `skills.manifest.json` in the given context directory and return its path.
        
        Parameters:
        	manifest (Dict): Manifest object to serialize to JSON.
        	context_root (Path): Directory where `skills.manifest.json` will be created; the directory will be created if it does not exist.
        
        Returns:
        	Path: The path to the written `skills.manifest.json` file (UTF-8 encoded, indented with 2 spaces).
        """
        context_root.mkdir(parents=True, exist_ok=True)
        path = context_root / "skills.manifest.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path

    def write_lock(self, selected: List[str], scored: Dict, context_root: Path) -> Path:
        """
        Write a skills lock file describing selected skills and their versions to the given context directory.
        
        Parameters:
            selected (List[str]): Ordered list of selected skill IDs to include in the lock.
            scored (Dict): Mapping of skill ID to scored entry; each entry must contain a `"skill"` dict with an optional `"version"` field.
            context_root (Path): Directory where `skills.lock.json` will be created; the directory is created if it does not exist.
        
        Returns:
            path (Path): Path to the written `skills.lock.json` file.
        """
        skills = []
        for skill_id in selected:
            skill = scored[skill_id]["skill"]
            skills.append(
                {
                    "id": skill_id,
                    "version": skill.get("version", "0.0.0"),
                }
            )
        lock = {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "skills": skills,
        }
        context_root.mkdir(parents=True, exist_ok=True)
        path = context_root / "skills.lock.json"
        path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        return path

    def _score_skill(
        self,
        skill: Dict,
        query_tokens: set,
        role_tokens: set,
        profile: Dict,
        skill_vectors: Optional[Dict[str, List[float]]],
        query_vector: Optional[List[float]],
        policy,
        guardrails: set,
        quality: Dict,
    ) -> Tuple[float, List[str]]:
        """
        Compute a composite relevance score for a single skill and collect contributing reasons.
        
        Parameters:
            skill (Dict): Skill metadata containing at least an "id", and optionally name, description, keywords, tags, role_affinity, tech, and domain fields used for scoring.
            query_tokens (set): Normalized tokens extracted from the assembled query text used for keyword overlap scoring.
            role_tokens (set): Tokens representing required/optional roles and agent names used for affinity scoring.
            profile (Dict): Profile snapshot (capabilities, tech stack, domains, nonfunctional requirements) used for tech/domain boosts and coverage signals.
            skill_vectors (Optional[Dict[str, List[float]]]): Mapping of skill id to embedding vectors used for cosine-similarity scoring; may be None to skip embedding scoring.
            query_vector (Optional[List[float]]): Embedding vector for the query text; required with skill_vectors to compute embedding similarity.
            policy: Policy object or namespace that provides scoring mode (e.g., `mode == "safety_first"`) and other policy-driven behavior.
            guardrails (set): IDs of skills treated as guardrails; used to apply safety boosts when policy requires.
            quality (Dict): Per-skill quality metrics mapping skill id to data (e.g., use_count, helpful_count, harmful_count) used to apply small penalties or boosts.
        
        Returns:
            Tuple[float, List[str]]: A tuple where the first element is the final composite score (higher is more relevant) and the second is a list of short reason strings describing contributing factors (e.g., `"embedding:0.82"`, `"keyword:0.40"`, `"tech_match"`, `"quality_penalty"`).
        """
        reasons = []
        embedding_score = 0.0
        if skill_vectors and query_vector and skill["id"] in skill_vectors:
            embedding_score = self._cosine_similarity(
                skill_vectors[skill["id"]], query_vector
            )
            if embedding_score > 0:
                reasons.append(f"embedding:{embedding_score:.2f}")

        keyword_score = self._keyword_score(skill, query_tokens)
        if keyword_score > 0:
            reasons.append(f"keyword:{keyword_score:.2f}")

        affinity_score = self._affinity_score(skill, role_tokens)
        if affinity_score > 0:
            reasons.append(f"affinity:{affinity_score:.2f}")

        score = (
            0.45 * embedding_score + 0.35 * keyword_score + 0.2 * affinity_score
        )

        # Boosts
        if self._tech_match(skill, profile):
            score += 0.15
            reasons.append("tech_match")
        if self._domain_match(skill, profile):
            score += 0.10
            reasons.append("domain_match")
        if policy.mode == "safety_first" and (
            skill.get("guardrail") or skill.get("id") in guardrails
        ):
            score += 0.20
            reasons.append("guardrail_boost")

        # Quality penalties/boosts
        q = quality.get(skill["id"])
        if q and q.get("use_count", 0) >= 3:
            helpful = q.get("helpful_count", 0)
            harmful = q.get("harmful_count", 0)
            ratio = helpful / max(1, helpful + harmful)
            if ratio < 0.4:
                score -= 0.15
                reasons.append("quality_penalty")
            elif ratio > 0.7:
                score += 0.05
                reasons.append("quality_boost")

        return score, reasons

    def _keyword_score(self, skill: Dict, query_tokens: set) -> float:
        """
        Scores how well a skill's textual fields match a set of query tokens.
        
        Builds a token set from the skill's name, description, keywords, and tags, then returns a normalized overlap score capped at 1.0. The overlap is divided by the larger of 3 or the number of query tokens to avoid inflated scores for very small queries.
        
        Parameters:
            skill (Dict): Skill metadata containing fields like `name`, `description`, `keywords`, and `tags`.
            query_tokens (set): Token set extracted from the query text.
        
        Returns:
            float: A score between 0.0 and 1.0 indicating keyword overlap; higher values indicate greater overlap.
        """
        skill_tokens = set(_tokenize(skill.get("name", "")))
        skill_tokens |= set(_tokenize(skill.get("description", "")))
        skill_tokens |= set(_tokenize(" ".join(skill.get("keywords", []))))
        skill_tokens |= set(_tokenize(" ".join(skill.get("tags", []))))
        if not query_tokens:
            return 0.0
        overlap = len(query_tokens.intersection(skill_tokens))
        return min(1.0, overlap / max(3, len(query_tokens)))

    def _affinity_score(self, skill: Dict, role_tokens: set) -> float:
        """
        Compute how well a skill's declared role affinities match a set of role tokens.
        
        Parameters:
            skill (Dict): Skill metadata; may contain a "role_affinity" iterable of role names.
            role_tokens (set): Normalized tokens representing roles to match against.
        
        Returns:
            float: A score between 0.0 and 1.0 equal to the fraction of role_tokens present in the skill's role_affinity, capped at 1.0.
        """
        if not role_tokens:
            return 0.0
        affinity = _safe_set(skill.get("role_affinity", []))
        if not affinity:
            return 0.0
        overlap = len(role_tokens.intersection(affinity))
        return min(1.0, overlap / max(1, len(role_tokens)))

    def _tech_match(self, skill: Dict, profile: Dict) -> bool:
        """
        Determine whether the skill's listed technologies intersect with the profile's technology stack.
        
        Parameters:
            skill (Dict): Skill metadata; expected to contain a "tech" iterable of technology names.
            profile (Dict): Profile data containing a "tech_stack" mapping with keys "languages", "frameworks", "datastores", and "infra".
        
        Returns:
            `True` if any normalized technology from the skill appears in the profile's tech stack, `False` otherwise.
        """
        tech = _safe_set(skill.get("tech", []))
        stack = profile.get("tech_stack", {})
        profile_tech = set(
            (stack.get("languages") or [])
            + (stack.get("frameworks") or [])
            + (stack.get("datastores") or [])
            + (stack.get("infra") or [])
        )
        return bool(tech.intersection(_safe_set(list(profile_tech))))

    def _domain_match(self, skill: Dict, profile: Dict) -> bool:
        """
        Determine whether the skill and profile share any domain tags.
        
        Parameters:
            skill (Dict): Skill metadata; expected to contain an optional "domains" list of strings.
            profile (Dict): Profile data; expected to contain an optional "domains" list of strings.
        
        Returns:
            True if there is at least one domain present in both the skill and the profile, False otherwise.
        """
        domains = _safe_set(skill.get("domains", []))
        profile_domains = _safe_set(profile.get("domains", []))
        return bool(domains.intersection(profile_domains))

    def _apply_budget(
        self,
        selected: set,
        scored: Dict,
        protected: set,
        profile: Dict,
        max_skills: int,
    ) -> set:
        """
        Reduce the selected skill set to fit within a maximum budget while preserving protected skills and favoring higher-ranked items that improve profile coverage.
        
        Parameters:
            selected (set): Candidate skill IDs currently selected.
            scored (Dict): Mapping of skill ID to scoring info; used to rank non-protected skills.
            protected (set): Skill IDs that must be preserved if present in `selected`.
            profile (Dict): Profile data whose capabilities and nonfunctional requirements are used to compute coverage-based preference.
            max_skills (int): Maximum number of skills to keep.
        
        Returns:
            set: Final set of kept skill IDs (contains all protected skills present in `selected`; additional slots filled by highest-ranked non-protected skills based on score and profile coverage).
        """
        if len(selected) <= max_skills:
            return selected

        kept = set(protected).intersection(selected)
        remaining_slots = max(0, max_skills - len(kept))

        coverage_terms = _safe_set(
            (profile.get("capabilities") or [])
            + (profile.get("requirements", {}).get("nonfunctional") or [])
        )

        ranked = []
        for skill_id in selected:
            if skill_id in kept:
                continue
            score = scored[skill_id]["score"]
            coverage = self._coverage_score(scored[skill_id]["skill"], coverage_terms)
            rank = score + min(0.2, 0.05 * coverage)
            ranked.append((rank, skill_id))

        ranked.sort(reverse=True)
        for _, skill_id in ranked:
            if len(kept) >= max_skills:
                break
            kept.add(skill_id)

        return kept

    def _coverage_score(self, skill: Dict, coverage_terms: set) -> int:
        """
        Compute how many terms from coverage_terms are provided or described by the skill.
        
        Parameters:
        	skill (Dict): Skill metadata containing optional "provides", "tags", and "keywords" lists of strings.
        	coverage_terms (set): Set of normalized tokens to check for coverage.
        
        Returns:
        	int: The count of tokens in coverage_terms that appear in the skill's provides, tags, or keywords.
        """
        if not coverage_terms:
            return 0
        skill_terms = set(_tokenize(" ".join(skill.get("provides", []))))
        skill_terms |= set(_tokenize(" ".join(skill.get("tags", []))))
        skill_terms |= set(_tokenize(" ".join(skill.get("keywords", []))))
        return len(coverage_terms.intersection(skill_terms))

    def _build_manifest(
        self,
        config: AgencyConfig,
        selected: set,
        scored: Dict,
        profile: Dict,
        required_skill_ids: set,
        guardrails: set,
        include_skills: set,
        inferred: set,
        excluded: List[Dict],
        policy,
    ) -> Dict:
        """
        Build a manifest summarizing the selected skills and surrounding selection context for the given project configuration.
        
        Parameters:
            config (AgencyConfig): Project-level configuration containing at least `project_name`.
            selected (set): Set of selected skill IDs to include in the manifest.
            scored (Dict): Mapping from skill ID to scoring metadata (expects keys `score` and `reasons` for each skill).
            profile (Dict): Snapshot of the computed profile used during selection.
            required_skill_ids (set): Skill IDs explicitly required by the config.
            guardrails (set): Skill IDs designated as guardrails by policy.
            include_skills (set): Skill IDs explicitly included by policy.
            inferred (set): Skill IDs inferred by the selection process.
            excluded (List[Dict]): List of exclusion records describing skills removed and reasons.
            policy: Policy object exposing at least `mode`, `max_skills`, and `min_score`.
        
        Returns:
            Dict: Manifest containing:
                - `project`: project name from `config`.
                - `generated_at`: ISO 8601 UTC timestamp when the manifest was generated.
                - `policy`: snapshot of policy fields (`mode`, `max_skills`, `min_score`).
                - `skills`: ordered list of skill entries; each entry has `id`, `score` (rounded to 4 decimals), `reasons`, and `required_by` (list indicating why the skill was selected).
                - `excluded`: the provided exclusion records.
                - `profile_snapshot`: the provided `profile`.
        """
        skills = []
        for skill_id in sorted(selected):
            meta = scored[skill_id]
            required_by = []
            if skill_id in required_skill_ids:
                required_by.append("required_skills")
            if skill_id in guardrails:
                required_by.append("guardrail")
            if skill_id in include_skills:
                required_by.append("include")
            if skill_id in inferred:
                required_by.append("inferred")
            skills.append(
                {
                    "id": skill_id,
                    "score": round(meta["score"], 4),
                    "reasons": meta["reasons"],
                    "required_by": required_by,
                }
            )

        return {
            "project": config.project_name,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "policy": {
                "mode": policy.mode,
                "max_skills": policy.max_skills,
                "min_score": policy.min_score,
            },
            "skills": skills,
            "excluded": excluded,
            "profile_snapshot": profile,
        }

    def _build_query_text(self, config: AgencyConfig, profile: Dict) -> str:
        """
        Constructs a space-separated query string from configuration and profile fields.
        
        Concatenates project requirements, functional and nonfunctional requirements, declared capabilities,
        profile domains, and tech-stack items (languages, frameworks, datastores, infra). Empty or missing
        parts are omitted and the result is trimmed.
        
        Parameters:
            config (AgencyConfig): Configuration containing project_requirements, requirements (functional, nonfunctional),
                and capabilities.
            profile (dict): Profile snapshot containing optional 'domains' and 'tech_stack' with keys
                'languages', 'frameworks', 'datastores', and 'infra'.
        
        Returns:
            query_text (str): A single trimmed string composed of the non-empty parts joined by spaces.
        """
        parts = [
            config.project_requirements or "",
            config.requirements.functional or "",
            " ".join(config.requirements.nonfunctional),
            " ".join(config.capabilities),
            " ".join(profile.get("domains", [])),
            " ".join(profile.get("tech_stack", {}).get("languages", [])),
            " ".join(profile.get("tech_stack", {}).get("frameworks", [])),
            " ".join(profile.get("tech_stack", {}).get("datastores", [])),
            " ".join(profile.get("tech_stack", {}).get("infra", [])),
        ]
        return " ".join([p for p in parts if p]).strip()

    def _extract_names(self, raw_list: List) -> List[str]:
        """
        Extracts names from a mixed list of strings and dictionaries.
        
        Parameters:
            raw_list (List): Iterable of items where each item is either a string or a dict. For dict items, this function looks for the first present key among `"skill"`, `"role"`, or `"name"` and uses its value.
        
        Returns:
            List[str]: Collected name strings in the original order; items without a usable name are skipped.
        """
        names = []
        for item in raw_list:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                val = item.get("skill") or item.get("role") or item.get("name")
                if val:
                    names.append(val)
        return names

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Compute similarity between two numeric vectors as their dot product.
        
        Parameters:
            a (List[float]): First numeric vector.
            b (List[float]): Second numeric vector.
        
        Returns:
            float: The dot product of `a` and `b`. Returns `0.0` if either input is empty or their lengths differ.
        """
        if not a or not b or len(a) != len(b):
            return 0.0
        return sum(x * y for x, y in zip(a, b))

    def _load_skill_quality(self) -> Dict:
        """
        Load per-skill quality metadata from the HQ knowledge store.
        
        Returns:
            dict: Mapping of skill IDs to quality metadata from `skill_quality.json` under the HQ `knowledge` directory; returns an empty dict if the file is missing or cannot be read/parsed.
        """
        quality_file = self.hq_path / "knowledge" / "skill_quality.json"
        if not quality_file.exists():
            return {}
        try:
            payload = json.loads(quality_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload.get("skills", {})