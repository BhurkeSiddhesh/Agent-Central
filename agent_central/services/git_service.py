import os

from git import GitCommandError, Repo


class GitService:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
        except Exception:
            self.repo = None

    def is_git_repo(self) -> bool:
        return self.repo is not None

    def get_current_branch(self) -> str:
        if not self.repo:
            return ""
        return self.repo.active_branch.name

    def list_branches(self):
        if not self.repo:
            return []
        return [h.name for h in self.repo.heads]

    def checkout(self, branch_name: str):
        if not self.repo:
            return
        self.repo.git.checkout(branch_name)

    def merge(self, branch_name: str):
        if not self.repo:
            return
        self.repo.git.merge(branch_name)
