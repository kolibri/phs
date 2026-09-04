from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BashRun:
    script: str
    root: bool = False

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Running command {self.script}")

        target.runner.run(
            ["bash", "-s"],
            root=self.root,
            input_text=self.script,
        )
