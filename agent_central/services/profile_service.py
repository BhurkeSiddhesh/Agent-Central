import json
import re
from pathlib import Path
from typing import Dict, List, Union

from agent_central.models.agency_config import AgencyConfig


def _normalize(items: List[str], preserve_case: bool = False) -> List[str]:
    normalized = {i.strip() for i in items if i and i.strip()}
    if not preserve_case:
        normalized = {i.lower() for i in normalized}
    return sorted(normalized)


class ProfileService:
    def __init__(self, project_root: Union[str, Path]):
        self.project_root = Path(project_root).resolve()

    def build_profile(self, config: AgencyConfig) -> Dict:
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
        context_root.mkdir(parents=True, exist_ok=True)
        out_path = context_root / "project.profile.json"
        out_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return out_path

    def _scan_repo(self) -> Dict[str, List[str]]:
        languages: List[str] = []
        frameworks: List[str] = []
        datastores: List[str] = []
        infra: List[str] = []
        sources: List[str] = []

        def add_from_file(path: Path, keywords: Dict[str, List[str]]):
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
        docker_compose_yml = self.project_root / "docker-compose.yml"
        docker_compose_yaml = self.project_root / "docker-compose.yaml"
        if docker_compose_yml.exists():
            infra.append("docker-compose")
            sources.append("docker-compose.yml")
        elif docker_compose_yaml.exists():
            infra.append("docker-compose")
            sources.append("docker-compose.yaml")
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
            "sources": _normalize(sources, preserve_case=True),
        }
