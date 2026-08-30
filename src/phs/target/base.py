from dataclasses import dataclass
from pathlib import Path
from typing import final, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str | None
    stderr: str | None


@final
class TargetCommandError(RuntimeError):
    result: CommandResult

    def __init__(self, result: CommandResult) -> None:
        self.result = result

        message = (
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(result.command)}"
        )

        if result.stderr:
            message += f"\n{result.stderr.rstrip()}"

        super().__init__(message)


class Target(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        root: bool = False,
        input_text: str | None = None,
        capture_output: bool = False,
        check: bool = True,
    ) -> CommandResult:
        ...

    def exists(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> bool:
        ...

    def read_text(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> str:
        ...

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> None:
        ...
