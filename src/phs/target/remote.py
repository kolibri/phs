import shlex
import subprocess
from pathlib import Path
from typing import Sequence, final, override

from phs.target.base import CommandResult, Target, TargetCommandError


@final
class RemoteTarget(Target):
    host: str
    user: str
    port: int
    identity_file: Path | None

    def __init__(
        self,
        host: str,
        user: str,
        *,
        port: int = 22,
        identity_file: Path | None = None,
    ) -> None:
        self.host = host
        self.user = user
        self.port = port
        self.identity_file = identity_file

    def _ssh_options(self) -> list[str]:
        options = [
            "-p",
            str(self.port),
        ]

        if self.identity_file is not None:
            options.extend([
                "-i",
                str(self.identity_file),
            ])

        return options

    def _ssh_command(
        self,
        command: Sequence[str],
        *,
        root: bool,
    ) -> list[str]:
        remote_command = list(command)

        if not remote_command:
            raise ValueError("Command must not be empty")

        if root:
            remote_command = [
                "sudo",
                "-n",
                "--",
                *remote_command,
            ]

        return [
            "ssh",
            *self._ssh_options(),
            f"{self.user}@{self.host}",
            shlex.join(remote_command),
        ]

    @property
    def description(self) -> str:
        return f"ssh {self.user}@{self.host}:{self.port}"

    @override
    def run(
        self,
        command: Sequence[str],
        *,
        root: bool = False,
        input_text: str | None = None,
        capture_output: bool = False,
        check: bool = True,
    ) -> CommandResult:
        actual_command = self._ssh_command(
            command,
            root=root,
        )

        completed = subprocess.run(
            actual_command,
            input=input_text,
            text=True,
            capture_output=capture_output,
            check=False,
        )

        result = CommandResult(
            command=tuple(actual_command),
            returncode=completed.returncode,
            stdout=completed.stdout if capture_output else None,
            stderr=completed.stderr if capture_output else None,
        )

        if check and result.returncode != 0:
            raise TargetCommandError(result)

        return result

    @override
    def exists(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> bool:
        result = self.run(
            ["test", "-e", str(path)],
            root=root,
            capture_output=True,
            check=False,
        )

        return result.returncode == 0

    @override
    def read_text(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> str:
        result = self.run(
            ["cat", "--", str(path)],
            root=root,
            capture_output=True,
        )

        if result.stdout is None:
            raise RuntimeError("Expected captured command output")

        return result.stdout

    @override
    def write_text(
        self,
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> None:
        self.run(
            ["tee", "--", str(path)],
            root=root,
            input_text=content,
            capture_output=True,
        )

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

            self.run(
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
                *self._ssh_options(),
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
            f"{self.user}@{self.host}:{destination}",
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