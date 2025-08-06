import os
from pathlib import Path
from git import Repo, GitCommandError

class GitRepo:
    def __init__(self, repo_path: str | Path, remote_name: str='origin'):
        self.repo = Repo(repo_path, search_parent_directories=True) #type: ignore
        self.remote_name = remote_name
        self.repo_path = self.repo.working_dir
        try:
            self.branch = self.repo.active_branch.name
        except TypeError:
            self.branch = self.repo.head.reference.name

    @property
    def remote_url(self):
        name = self.remote_name
        if name not in self.repo.remotes:
            raise ValueError(f"Remote '{name}' not found")
        remote = self.repo.remotes[name]
        urls = list(remote.urls)
        if not urls:
            raise ValueError(f"Remote '{name}' has no configured URLs")
        return urls[0]

    def fetch_and_ff(self):
        origin = self.repo.remotes[self.remote_name]
        origin.fetch()
        self.repo.git.merge('--ff-only', 'FETCH_HEAD')

    def pull(self) -> bool:
        origin = self.repo.remotes[self.remote_name]
        return origin.pull(self.branch)

    def revert_file(self, file_path) -> bool:
        rel_path = os.path.relpath(file_path, self.repo_path)
        try:
            self.repo.git.checkout('--', rel_path)
            return True
        except GitCommandError as e:
            return False

    def stage_file(self, file_path):
        rel_path = os.path.relpath(file_path, self.repo_path)
        self.repo.index.add([rel_path])
        self.repo.index.write()

    def create_commit(self, message):
        return self.repo.index.commit(message)

    def has_changes(self, include_untracked=True):
        return self.repo.is_dirty(untracked_files=include_untracked)

    def has_file_changes(self, file_path, include_untracked=True):
        rel = os.path.relpath(file_path, self.repo_path)
        if include_untracked and rel in self.repo.untracked_files:
            return True
        diffs = self.repo.index.diff(None) + self.repo.index.diff('HEAD')
        return any(item.a_path == rel for item in diffs)

    def push_changes(self):
        origin = self.repo.remotes[self.remote_name]
        return origin.push(self.branch)

    def will_conflict(self, file_path):
        origin = self.repo.remotes[self.remote_name]
        origin.fetch()
        remote_ref = f'{self.remote_name}/{self.branch}'
        rel = os.path.relpath(file_path, self.repo_path)
        try:
            self.repo.git.merge('--no-commit', '--no-ff', remote_ref)
        except GitCommandError:
            pass
        conflicts = self.repo.index.unmerged_blobs()
        has_conflict = rel in conflicts
        try:
            self.repo.git.merge('--abort')
        except GitCommandError:
            pass
        return has_conflict

    # Assembled

    def commit_changes(self, message, file_path):
        try:
            self.fetch_and_ff()
            self.stage_file(file_path)
            self.create_commit(message)
            self.push_changes()
            return True

        except GitCommandError as e:
            print("Git operation failed:", e)
            return False