import os
import subprocess
from pathlib import Path
from typing import final, Sequence, override

from phs.target.base import Target, CommandResult, TargetCommandError


@final
class LocalTarget(Target):
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
        if not root or os.geteuid() == 0:
            path.write_text(
                content,
                encoding="utf-8",
            )
            return

        self.run(
            ["tee", "--", str(path)],
            root=True,
            input_text=content,
            capture_output=True,
        )
