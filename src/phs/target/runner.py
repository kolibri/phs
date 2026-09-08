from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, final, override

from phs.output import Output
from phs.target.base import CommandResult

type OutputCallback = Callable[[str], None]


class Runner(Protocol):
    @property
    def dry_run(self) -> bool:
        """Whether tasks should preview work without querying external state."""
        return False

    @property
    def description(self) -> str: ...

    def run(
        self,
        command: Sequence[str],
        *,
        root: bool = False,
        cwd: Path | None = None,
        input_text: str | None = None,
        capture_output: bool = False,
        check: bool = True,
        on_output: OutputCallback | None = None,
    ) -> CommandResult: ...


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
    def dry_run(self) -> bool:
        return self.runner.dry_run

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
        cwd: Path | None = None,
        input_text: str | None = None,
        capture_output: bool = False,
        check: bool = True,
        on_output: OutputCallback | None = None,
    ) -> CommandResult:
        if capture_output:
            return self.runner.run(
                command,
                root=root,
                cwd=cwd,
                input_text=input_text,
                capture_output=True,
                check=check,
            )

        return self.runner.run(
            command,
            root=root,
            cwd=cwd,
            input_text=input_text,
            check=check,
            on_output=(on_output if on_output is not None else self.output.text),
        )
