from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class ServiceDaemonReload:
    def execute(self, target: TargetContext) -> None:
        target.output.info("Reloading systemd configuration")
        target.runner.run(
            ["systemctl", "daemon-reload"],
            root=True,
        )
