from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


def _search_name(font: str) -> str:
    if font.startswith("google-"):
        return font.removeprefix("google-")

    if font.startswith("fonts-"):
        return font.removeprefix("fonts-")

    return font

@final
@dataclass(frozen=True, slots=True)
class FntInstall:
    fonts: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        for font in self.fonts:

            result = target.runner.run(["fnt", "search", _search_name(font)], capture_output=True)

            target.output.info(f"##{font}##")

            matches = {
                line.strip()
                for line in (result.stdout or "").splitlines()
                if line.strip()
            }
            for match in matches:
                target.output.info(f"+#{match}##")

            if font not in matches:
                target.output.error(f"Font {font} not found in catalog!")
                raise ValueError(f"Font {font} not found")


            target.output.info(f"Ensuring font {font}")
            target.runner.run([
                "fnt",
                "install",
                font,
            ])
