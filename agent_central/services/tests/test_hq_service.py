import pytest
import shutil
from pathlib import Path
from agent_central.services.hq_service import HQService

@pytest.fixture
def hq_setup(tmp_path):
    """Sets up a mock HQ structure in a temporary directory."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    hq_dir = project_root / ".agency-hq"
    hq_dir.mkdir()

    (hq_dir / "skills").mkdir()
    (hq_dir / "roles").mkdir()

    # Create a dummy skill
    skill_dir = hq_dir / "skills" / "python-pro"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Skill: python-pro\nDescription: Expert python dev", encoding="utf-8")
    (skill_dir / "README.md").write_text("# Python Pro\nExpert python dev", encoding="utf-8")

    # Create a dummy role
    (hq_dir / "roles" / "backend-dev.md").write_text("# Backend Dev", encoding="utf-8")

    return project_root

def test_list_skills(hq_setup):
    service = HQService(project_root=str(hq_setup))

    skills = service.list_skills()
    assert isinstance(skills, list)
    assert "python-pro" in skills
    assert len(skills) == 1

def test_infer_assets(hq_setup):
    service = HQService(project_root=str(hq_setup))

    roles, skills = service.infer_assets("I need a python backend developer")

    assert isinstance(roles, list)
    assert isinstance(skills, list)

    assert "backend-dev" in roles
    assert "python-pro" in skills

def test_caching(hq_setup):
    service = HQService(project_root=str(hq_setup))

    # First call
    skills1 = service.list_skills()

    # Second call (should be cached)
    skills2 = service.list_skills()

    assert skills1 == skills2
    assert service._skills_list_cache is not None
    assert service._skills_list_cache is skills2 # Identity check
