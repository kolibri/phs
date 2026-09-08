from phs.tasks.pacman_update import PacmanUpdate


def test_updates_packages(target):
    PacmanUpdate().execute(target)
    target.runner.run.assert_called_once_with(
        ["pacman", "-Syu", "--noconfirm"], root=True
    )
