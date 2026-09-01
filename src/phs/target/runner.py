from collections.abc import Sequence
from typing import Protocol

from phs.target.base import CommandResult


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
