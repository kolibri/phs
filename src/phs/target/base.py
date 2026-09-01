from dataclasses import dataclass
from typing import final


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
