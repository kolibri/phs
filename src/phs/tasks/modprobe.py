from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class ModprobeLoad:
    modules: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        for module in self.modules:
            config_path = Path(
                f"/etc/modules-load.d/phs-{module}.conf"
            )

            content = f"{module}\n"

            current_content = (
                target.filesystem.read_text(config_path, root=True)
                if target.filesystem.exists(config_path, root=True)
                else None
            )

            if current_content != content:
                target.filesystem.write_text(config_path, content, root=True)

            target.runner.run(
                ["modprobe", module],
                root=True,
            )


@final
class Modprobe:
    @staticmethod
    def load(modules: list[str]) -> Task:
        return ModprobeLoad(
            modules=tuple(modules),
        )
