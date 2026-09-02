from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class FntUpdate:
    def execute(self, target: TargetContext) -> None:
        target.output.info("Updating font index")
        target.runner.run([
            "fnt",
            "update",
        ])


@final
@dataclass(frozen=True, slots=True)
class FntInstall:
    fonts: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        for font in self.fonts:
            target.output.info(f"Ensuring font {font}")
            target.runner.run([
                "fnt",
                "install",
                font,
            ])


@final
class Fnt:
    @staticmethod
    def update() -> Task:
        return FntUpdate()

    @staticmethod
    def install(fonts: list[str]) -> Task:
        return FntInstall(
            fonts=tuple(fonts),
        )