from collections.abc import Sequence
from typing import Protocol
from typing import final, override

from phs.output import Output
from phs.target.base import CommandResult, TargetCommandError


class Runner(Protocol):
    @property
    def description(self) -> str:
        ...

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


@final
class OutputRunner(Runner):
    def __init__(
            self,
            runner: Runner,
            output: Output,
    ) -> None:
        self.runner = runner
        self.output = output

    @property
    @override
    def description(self) -> str:
        return self.runner.description

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
        if capture_output:
            return self.runner.run(
                command,
                root=root,
                input_text=input_text,
                capture_output=True,
                check=check,
            )

        result = self.runner.run(
            command,
            root=root,
            input_text=input_text,
            capture_output=True,
            check=False,
        )

        if result.stdout:
            self.output.text(result.stdout.rstrip())

        if result.stderr:
            self.output.text(result.stderr.rstrip())

        if check and result.returncode != 0:
            raise TargetCommandError(result)

        return CommandResult(
            command=result.command,
            returncode=result.returncode,
            stdout=None,
            stderr=None,
        )
