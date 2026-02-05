import json
import re
from pathlib import Path
from typing import Dict, List, Union

from agent_central.models.agency_config import AgencyConfig


def _normalize(items: List[str]) -> List[str]:
    """
    Normalize a list of strings by trimming whitespace, converting to lowercase, removing empty entries, deduplicating, and returning them in sorted order.
    
    Parameters:
        items (List[str]): Strings to normalize.
    
    Returns:
        List[str]: Sorted, deduplicated, lowercase strings with surrounding whitespace removed; empty or whitespace-only entries are omitted.
    """
    return sorted({i.strip().lower() for i in items if i and i.strip()})


class ProfileService:
    def __init__(self, project_root: Union[str, Path]):
        """
        Initialize the service with the project root path.
        
        Parameters:
            project_root (Union[str, Path]): Path to the project's root directory; converted to a Path and resolved to an absolute path.
        """
        self.project_root = Path(project_root).resolve()

    def build_profile(self, config: AgencyConfig) -> Dict:
        """
        Builds a normalized project profile dictionary by combining values from the provided AgencyConfig with repository-derived scan results.
        
        Parameters:
            config (AgencyConfig): Project configuration containing metadata, profile fields (domains, tech_stack, constraints), capabilities, and requirements.
        
        Returns:
            dict: Profile with the following keys:
                - project_name: project name from config
                - project_description: project description from config
                - domains: normalized list of domains
                - tech_stack: dict with normalized lists for `languages`, `frameworks`, `datastores`, and `infra`
                - constraints: normalized list of constraints
                - capabilities: normalized list of capabilities
                - requirements: dict containing `functional` (from config) and `nonfunctional` (normalized) requirements
                - sources: dict with `repo_scan` listing repository file paths that contributed to the scan
        """
        scan = self._scan_repo()

        profile = {
            "project_name": config.project_name,
            "project_description": config.project_description,
            "domains": _normalize(config.project_profile.domains),
            "tech_stack": {
                "languages": _normalize(
                    config.project_profile.tech_stack.languages + scan["languages"]
                ),
                "frameworks": _normalize(
                    config.project_profile.tech_stack.frameworks + scan["frameworks"]
                ),
                "datastores": _normalize(
                    config.project_profile.tech_stack.datastores + scan["datastores"]
                ),
                "infra": _normalize(
                    config.project_profile.tech_stack.infra + scan["infra"]
                ),
            },
            "constraints": _normalize(config.project_profile.constraints),
            "capabilities": _normalize(config.capabilities),
            "requirements": {
                "functional": config.requirements.functional,
                "nonfunctional": _normalize(config.requirements.nonfunctional),
            },
            "sources": {
                "repo_scan": scan["sources"],
            },
        }

        return profile

    def write_profile(self, profile: Dict, context_root: Path) -> Path:
        """
        Write a profile dictionary as formatted JSON to a file named `project.profile.json` inside the given context directory.
        
        Parameters:
            profile (Dict): The profile data to serialize to JSON.
            context_root (Path): Directory to create (if needed) and place the output file.
        
        Returns:
            out_path (Path): Path to the written `project.profile.json` file.
        """
        context_root.mkdir(parents=True, exist_ok=True)
        out_path = context_root / "project.profile.json"
        out_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return out_path

    def _scan_repo(self) -> Dict[str, List[str]]:
        """
        Scan the project root for languages, frameworks, datastores, infrastructure, and source file references.
        
        Detects languages by presence of common manifest files (e.g., pyproject.toml, package.json, go.mod, pom.xml, Cargo.toml), discovers frameworks and datastores by searching dependency files for well-known keywords, and detects infra artifacts (Docker, docker-compose, GitHub Actions, Kubernetes) by checking for typical files and directories. Unreadable files are ignored. Returns normalized, deduplicated, lowercased, sorted lists for each category.
        
        Returns:
            Dict[str, List[str]]: A mapping with keys "languages", "frameworks", "datastores", "infra", and "sources", each containing a list of detected values.
        """
        languages: List[str] = []
        frameworks: List[str] = []
        datastores: List[str] = []
        infra: List[str] = []
        sources: List[str] = []

        def add_from_file(path: Path, keywords: Dict[str, List[str]]):
            """
            Scan a file for dependency keywords and record any detected frameworks, datastores, or infra along with the file source.
            
            Reads the file at `path` (UTF-8, ignoring read errors). For each keyword group in `keywords`, performs a whole-word, case-insensitive search for each value; when a value is found it is appended to the corresponding outer-scope list (`frameworks`, `datastores`, or `infra`). Regardless of matches, the file's path relative to `self.project_root` is appended to the outer-scope `sources` list. Read errors are ignored silently.
            
            Parameters:
                path (Path): Path to the file to scan.
                keywords (Dict[str, List[str]]): Mapping of keyword groups to lists of keyword strings to search for. Expected keys include `"frameworks"`, `"datastores"`, and `"infra"`.
            """
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                return
            for key, values in keywords.items():
                for val in values:
                    if re.search(rf"\\b{re.escape(val)}\\b", text):
                        if key == "frameworks":
                            frameworks.append(val)
                        elif key == "datastores":
                            datastores.append(val)
                        elif key == "infra":
                            infra.append(val)
            sources.append(str(path.relative_to(self.project_root)))

        # Language detection
        if (self.project_root / "pyproject.toml").exists() or (
            self.project_root / "requirements.txt"
        ).exists():
            languages.append("python")
        if (self.project_root / "package.json").exists():
            languages.append("javascript")
        if (self.project_root / "go.mod").exists():
            languages.append("go")
        if (self.project_root / "pom.xml").exists():
            languages.append("java")
        if (self.project_root / "Cargo.toml").exists():
            languages.append("rust")

        # Frameworks + datastores from dependency files
        dep_keywords = {
            "frameworks": [
                "django",
                "flask",
                "fastapi",
                "react",
                "vue",
                "next",
                "svelte",
                "express",
                "nestjs",
                "spring",
            ],
            "datastores": [
                "postgres",
                "postgresql",
                "mysql",
                "mariadb",
                "sqlite",
                "mongodb",
                "redis",
                "dynamodb",
            ],
        }

        for dep_file in [
            self.project_root / "requirements.txt",
            self.project_root / "pyproject.toml",
            self.project_root / "package.json",
        ]:
            if dep_file.exists():
                add_from_file(dep_file, dep_keywords)

        # Infra detection
        if (self.project_root / "Dockerfile").exists():
            infra.append("docker")
            sources.append("Dockerfile")
        if (self.project_root / "docker-compose.yml").exists() or (
            self.project_root / "docker-compose.yaml"
        ).exists():
            infra.append("docker-compose")
            sources.append("docker-compose.yml")
        if (self.project_root / ".github" / "workflows").exists():
            infra.append("github-actions")
            sources.append(".github/workflows")
        if (self.project_root / "k8s").exists() or (
            self.project_root / "kubernetes"
        ).exists():
            infra.append("kubernetes")
            sources.append("k8s/")

        return {
            "languages": _normalize(languages),
            "frameworks": _normalize(frameworks),
            "datastores": _normalize(datastores),
            "infra": _normalize(infra),
            "sources": _normalize(sources),
        }