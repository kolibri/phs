from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


def _is_available(target: TargetContext) -> bool:
    result = target.runner.run(
        [
            "sh",
            "-c",
            "command -v fnt >/dev/null 2>&1",
        ],
        capture_output=True,
        check=False,
    )

    return result.returncode == 0


@final
@dataclass(frozen=True, slots=True)
class FntUpdate:
    def execute(self, target: TargetContext) -> None:
        if not _is_available(target):
            target.output.warning("Skipping font update: fnt is not installed")
            return

        target.output.info("Updating font index")
        target.runner.run([
            "fnt",
            "update",
        ])
