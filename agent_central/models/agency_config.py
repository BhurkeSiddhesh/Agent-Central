from __future__ import annotations

from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class TechStack(BaseModel):
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    datastores: List[str] = Field(default_factory=list)
    infra: List[str] = Field(default_factory=list)


class ProjectProfile(BaseModel):
    domains: List[str] = Field(default_factory=list)
    tech_stack: TechStack = Field(default_factory=TechStack)
    constraints: List[str] = Field(default_factory=list)


class Requirements(BaseModel):
    functional: Optional[str] = None
    nonfunctional: List[str] = Field(default_factory=list)


class SkillPolicy(BaseModel):
    mode: Literal["minimal", "balanced", "safety_first"] = "balanced"
    max_skills: int = Field(25, ge=1)
    min_score: float = Field(0.35, ge=0.0, le=1.0)
    embedding_weight: float = 0.45
    keyword_weight: float = 0.35
    affinity_weight: float = 0.20
    tech_boost: float = 0.15
    domain_boost: float = 0.10
    guardrail_boost: float = 0.20
    include_skills: List[str] = Field(default_factory=list)
    exclude_skills: List[str] = Field(default_factory=list)
    guardrail_skills: List[str] = Field(default_factory=list)


class RolePolicy(BaseModel):
    required_roles: List[str] = Field(default_factory=list)
    optional_roles: List[str] = Field(default_factory=list)


class AgencyConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: Optional[str] = None
    project_description: Optional[str] = None

    # Legacy fields (still supported)
    project_requirements: Optional[str] = None
    required_agents: List[Any] = Field(default_factory=list)
    required_skills: List[Any] = Field(default_factory=list)

    # New structured fields
    project_profile: ProjectProfile = Field(default_factory=ProjectProfile)
    capabilities: List[str] = Field(default_factory=list)
    requirements: Requirements = Field(default_factory=Requirements)
    skill_policy: SkillPolicy = Field(default_factory=SkillPolicy)
    role_policy: RolePolicy = Field(default_factory=RolePolicy)
