from collections.abc import Sequence
from pathlib import Path
from typing import final, override

from phs.target.base import CommandResult
from phs.target.runner import OutputCallback, Runner


@final
class DryRunRunner(Runner):
    runner: Runner

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    @property
    @override
    def dry_run(self) -> bool:
        return True

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
        prefix = "sudo " if root else ""

        print(f"[dry-run] [{self.runner.description}] {prefix}{' '.join(command)}")

        if cwd is not None:
            print(f"[dry-run] cwd: {cwd}")

        if input_text is not None:
            print("[dry-run] stdin:")
            print(input_text)

        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout=None,
            stderr=None,
        )
