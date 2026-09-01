from typing import final, override, Sequence

from phs.target.base import CommandResult
from phs.target.runner import Runner


@final
class DryRunRunner(Runner):
    runner: Runner

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

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
        prefix = "sudo " if root else ""

        print(
            f"[dry-run] [{self.runner.description}] "
            f"{prefix}{' '.join(command)}"
        )

        if input_text is not None:
            print("[dry-run] stdin:")
            print(input_text)

        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout=None,
            stderr=None,
        )
