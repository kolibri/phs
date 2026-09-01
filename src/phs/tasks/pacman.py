from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class PacmanUpdate:
    def execute(self, target: TargetContext) -> None:
        target.runner.run(
            [
                "pacman",
                "-Syu",
                "--noconfirm",
            ],
            root=True,
        )


@final
@dataclass(frozen=True, slots=True)
class PacmanInstall:
    packages: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        if not self.packages:
            return

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


@final
class Pacman:
    @staticmethod
    def update() -> Task:
        return PacmanUpdate()

    @staticmethod
    def install(packages: list[str]) -> Task:
        return PacmanInstall(tuple(packages))
