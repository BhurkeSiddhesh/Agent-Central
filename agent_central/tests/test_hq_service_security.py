import shutil
import unittest
from pathlib import Path

from agent_central.services.hq_service import HQService


class TestHQServiceSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_security_env")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

        # Create local HQ
        self.hq_dir = self.test_dir / ".agency-hq"
        self.hq_dir.mkdir()

        # Roles setup
        self.roles_dir = self.hq_dir / "roles"
        self.roles_dir.mkdir()
        (self.roles_dir / "valid_role.md").write_text(
            "Valid Role Content", encoding="utf-8"
        )

        # Skills setup
        self.skills_dir = self.hq_dir / "skills"
        self.skills_dir.mkdir()
        (self.skills_dir / "valid_skill").mkdir()
        (self.skills_dir / "valid_skill" / "SKILL.md").write_text(
            "Valid Skill Content", encoding="utf-8"
        )

        # Secrets setup (outside allowed dirs)
        (self.hq_dir / "secret.md").write_text("SECRET ROLE", encoding="utf-8")
        (self.hq_dir / "secret_skill").mkdir()
        (self.hq_dir / "secret_skill" / "SKILL.md").write_text(
            "SECRET SKILL", encoding="utf-8"
        )

        self.service = HQService(project_root=str(self.test_dir))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_get_role_content_valid(self):
        content = self.service.get_role_content("valid_role")
        self.assertEqual(content, "Valid Role Content")

    def test_get_role_content_traversal(self):
        # Attempt to access ../secret.md
        with self.assertRaises(ValueError) as cm:
            self.service.get_role_content("../secret")
        self.assertIn("Security Alert", str(cm.exception))
        self.assertIn("blocked", str(cm.exception))

    def test_get_skill_content_valid(self):
        content = self.service.get_skill_content("valid_skill")
        self.assertEqual(content, "Valid Skill Content")

    def test_get_skill_content_traversal(self):
        # Attempt to access ../secret_skill/SKILL.md
        with self.assertRaises(ValueError) as cm:
            self.service.get_skill_content("../secret_skill")
        self.assertIn("Security Alert", str(cm.exception))
        self.assertIn("blocked", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
