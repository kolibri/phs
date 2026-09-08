from pathlib import Path

import pytest

from phs.tasks.git_clone import GitClone


@pytest.mark.parametrize("branch", [None, "feature/topic", ""])
@pytest.mark.parametrize("update", [False, True])
def test_clones_missing_repository(target, branch, update):
    destination = Path("/srv/repo space")
    target.filesystem.exists.return_value = False
    GitClone("https://example.invalid/repo.git", destination, branch, update).execute(
        target
    )
    target.filesystem.exists.assert_called_once_with(destination / ".git")
    command = ["git", "clone"]
    if branch is not None:
        command += ["--branch", branch]
    command += ["--", "https://example.invalid/repo.git", str(destination)]
    target.runner.run.assert_called_once_with(command)


@pytest.mark.parametrize("update", [False, True])
def test_existing_repository_updates_only_on_request(target, update):
    target.filesystem.exists.return_value = True
    GitClone("unused", Path("/srv/repo"), update=update).execute(target)
    target.filesystem.exists.assert_called_once_with(Path("/srv/repo/.git"))
    if update:
        target.runner.run.assert_called_once_with(
            ["git", "-C", "/srv/repo", "pull", "--ff-only"]
        )
    else:
        target.runner.run.assert_not_called()
