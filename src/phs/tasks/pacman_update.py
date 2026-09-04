from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class PacmanUpdate:
    def execute(self, target: TargetContext) -> None:
        target.output.info("Updating pacman")

        target.runner.run(
            [
                "pacman",
                "-Syu",
                "--noconfirm",
            ],
            root=True,
        )
