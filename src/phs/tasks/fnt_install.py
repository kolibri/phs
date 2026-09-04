from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


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
