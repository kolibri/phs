import shlex
import subprocess
from pathlib import Path
from typing import final, Sequence, override

from phs.target.base import CommandResult, TargetCommandError
from phs.target.runner import OutputCallback, Runner


@final
class RemoteRunner(Runner):
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

    def ssh_options(self) -> list[str]:
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
            *self.ssh_options(),
            f"{self.user}@{self.host}",
            shlex.join(remote_command),
        ]

    @property
    @override
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
            on_output: OutputCallback | None = None,
    ) -> CommandResult:
        actual_command = self._ssh_command(
            command,
            root=root,
        )

        if on_output is not None and not capture_output:
            process = subprocess.Popen(
                actual_command,
                stdin=(
                    subprocess.PIPE
                    if input_text is not None
                    else None
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            if input_text is not None:
                if process.stdin is None:
                    raise RuntimeError("Expected subprocess stdin")

                try:
                    process.stdin.write(input_text)
                except BrokenPipeError:
                    pass
                finally:
                    process.stdin.close()

            if process.stdout is None:
                raise RuntimeError("Expected subprocess stdout")

            for line in process.stdout:
                on_output(
                    line.removesuffix("\n").removesuffix("\r")
                )

            result = CommandResult(
                command=tuple(actual_command),
                returncode=process.wait(),
                stdout=None,
                stderr=None,
            )
        else:
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
