from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class DirectoryCreate:
    path: Path
    root: bool = False

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Ensuring directory {self.path}")

        target.runner.run(
            [
                "mkdir",
                "-p",
                "--",
                str(self.path),
            ],
            root=self.root,
        )
