from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class ServiceEnable:
    services: tuple[str, ...]
    start: bool = True

    def execute(self, target: TargetContext) -> None:
        for service in self.services:
            enabled = target.runner.run(
                ["systemctl", "is-enabled", "--quiet", service],
                root=True,
                capture_output=True,
                check=False,
            ).returncode == 0

            active = (
                target.runner.run(
                    ["systemctl", "is-active", "--quiet", service],
                    root=True,
                    capture_output=True,
                    check=False,
                ).returncode == 0
                if self.start
                else True
            )

            if enabled and active:
                continue

            target.output.info(f"Enabling service {service}.")

            command = ["systemctl", "enable"]

            if self.start:
                command.append("--now")

            command.append(service)

            target.runner.run(
                command,
                root=True,
            )
