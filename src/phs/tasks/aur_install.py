from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.template import TemplateRenderer


@final
@dataclass(frozen=True, slots=True)
class AurInstall:
    packages: tuple[str, ...]
    renderer: TemplateRenderer

    def execute(self, target: TargetContext) -> None:
        for package in self.packages:
            script = self.renderer.render(
                "scripts/install_aur_package.sh.j2",
                package=package,
            )

            target.output.info(f"Ensuring aur package {package}")
            target.runner.run(
                [
                    "bash",
                    "-s",
                ],
                input_text=script,
            )
