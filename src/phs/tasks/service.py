from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class ServiceEnable:
    services: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        for service in self.services:
            target.runner.run(
                [
                    "systemctl",
                    "enable",
                    "--now",
                    service,
                ],
                root=True,
            )


@final
class Service:
    @staticmethod
    def enable(services: list[str]) -> Task:
        return ServiceEnable(
            services=tuple(services),
        )