from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class MountEnsure:
    target: Path

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Mounting {self.target}")

        result = target.runner.run(
            [
                "mountpoint",
                "--quiet",
                str(self.target),
            ],
            check=False,
        )

        if result.returncode == 0:
            return

        target.runner.run(
            [
                "mount",
                str(self.target),
            ],
            root=True,
        )
