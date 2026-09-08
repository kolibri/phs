from pathlib import Path

from phs.tasks.directory_create import DirectoryCreate


def test_creates_directory(target):
    task = DirectoryCreate(Path("/srv/example"))

    task.execute(target)

    target.runner.run.assert_called_once_with(
        [
            "mkdir",
            "-p",
            "--",
            "/srv/example",
        ],
        root=False,
    )


def test_creates_directory_as_root(target):
    task = DirectoryCreate(
        Path("/etc/example"),
        root=True,
    )

    task.execute(target)

    target.runner.run.assert_called_once_with(
        [
            "mkdir",
            "-p",
            "--",
            "/etc/example",
        ],
        root=True,
    )
