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
            target.output.info(f'Enabling service {service}.')


            command = ["systemctl", "enable"]

            if self.start:
                command.append("--now")

            command.append(service)

            target.runner.run(
                command,
                root=True,
            )


@final
class Service:
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