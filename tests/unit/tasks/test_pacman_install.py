import pytest

from phs.tasks.pacman_install import PacmanInstall


@pytest.mark.parametrize("packages", [("git",), ("git", "vim")])
def test_installs_only_needed_packages(target, packages):
    PacmanInstall(packages).execute(target)
    target.runner.run.assert_called_once_with(
        ["pacman", "-S", "--needed", "--noconfirm", *packages], root=True
    )


def test_empty_packages_do_nothing(target):
    PacmanInstall(()).execute(target)
    target.runner.run.assert_not_called()
