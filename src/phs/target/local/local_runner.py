import os
import subprocess
from typing import final, Sequence, override

from phs.target.base import CommandResult, TargetCommandError
from phs.target.runner import Runner


@final
class LocalRunner(Runner):
    @staticmethod
    def _command(
            command: Sequence[str],
            *,
            root: bool,
    ) -> list[str]:
        result = list(command)

        if not result:
            raise ValueError("Command must not be empty")

        if root and os.geteuid() != 0:
            return [
                "sudo",
                "-n",
                "--",
                *result,
            ]

        return result

    @property
    @override
    def description(self) -> str:
        return "local"

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
        actual_command = self._command(
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
