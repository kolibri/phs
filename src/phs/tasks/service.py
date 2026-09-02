from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class ServiceEnable:
    services: tuple[str, ...]
    start: bool

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


@final
@dataclass(frozen=True, slots=True)
class ServiceDaemonReload:
    def execute(self, target: TargetContext) -> None:
        target.output.info("Reloading systemd configuration")
        target.runner.run(
            ["systemctl", "daemon-reload"],
            root=True,
        )


@final
class Service:
    @staticmethod
    def daemon_reload() -> Task:
        return ServiceDaemonReload()

    @staticmethod
    def enable(
        services: list[str],
        *,
        start: bool = True,
    ) -> Task:
        return ServiceEnable(
            services=tuple(services),
            start=start,
        )
