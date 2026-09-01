from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class BashRun:
    script: str
    root: bool

    def execute(self, target: TargetContext) -> None:
        target.runner.run(
            ["bash", "-s"],
            root=self.root,
            input_text=self.script,
        )


@final
class Bash:
    @staticmethod
    def run(
        script: str,
        *,
        root: bool = False,
    ) -> Task:
        return BashRun(
            script=script,
            root=root,
        )