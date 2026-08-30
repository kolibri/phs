from dataclasses import dataclass
from typing import final

from phs.modules.task import Task
from phs.target.base import Target


@final
@dataclass(frozen=True, slots=True)
class PacmanUpdate:
    def execute(self, target: Target) -> None:
        target.run(
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

    def execute(self, target: Target) -> None:
        if not self.packages:
            return

        target.run(
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