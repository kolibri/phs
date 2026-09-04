from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class PacmanInstall:
    packages: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        if not self.packages:
            return

        target.output.info(f'Ensuring packages {" ".join(self.packages)}')

        target.runner.run(
            [
                "pacman",
                "-S",
                "--needed",
                "--noconfirm",
                *self.packages,
            ],
            root=True,
        )
