import shlex
import subprocess
from pathlib import Path
from typing import final, override, Sequence

from phs.target.base import TargetCommandError, CommandResult
from phs.target.remote.remote_runner import RemoteRunner
from phs.target.transfer import Transfer


@final
class RemoteTransfer(Transfer):
    runner: RemoteRunner

    def __init__(self, runner: RemoteRunner) -> None:
        self.runner = runner

    @property
    @override
    def description(self) -> str:
        return self.runner.description

    @override
    def transfer(
        self,
        source: Path,
        destination: Path,
        *,
        root: bool = False,
        create_dirs: bool = False,
        exclude: Sequence[str] = (),
    ) -> None:
        if not source.exists():
            raise FileNotFoundError(source)

        if create_dirs:
            directory = (
                destination
                if source.is_dir()
                else destination.parent
            )

            self.runner.run(
                ["mkdir", "-p", "--", str(directory)],
                root=root,
            )

        exclude_args: list[str] = []

        for pattern in exclude:
            exclude_args.extend([
                "--exclude",
                pattern,
            ])

        source_arg = (
            f"{source}/"
            if source.is_dir()
            else str(source)
        )

        command = [
            "rsync",
            "-a",
            "--protect-args",
            "-e",
            shlex.join([
                "ssh",
                *self.runner.ssh_options(),
            ]),
            *exclude_args,
        ]

        if root:
            command.extend([
                "--rsync-path",
                "sudo -n -- rsync",
            ])

        command.extend([
            "--",
            source_arg,
            f"{self.runner.user}@{self.runner.host}:{destination}",
        ])

        completed = subprocess.run(
            command,
            check=False,
        )

        if completed.returncode != 0:
            raise TargetCommandError(
                CommandResult(
                    command=tuple(command),
                    returncode=completed.returncode,
                    stdout=None,
                    stderr=None,
                )
            )
