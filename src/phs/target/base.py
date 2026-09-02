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
        super().__init__("Target command failed")