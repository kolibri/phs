from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.pacman import Pacman
from phs.tasks.service import Service
from phs.tasks.task import Task
from phs.tasks.user import User


@final
class Docker:
    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        return [
            Pacman.install([
                "docker",
                "docker-buildx",
                "docker-compose",
            ]),

            User.ensure_groups(
                data.username,
                ["docker"],
            ),

            Service.enable([
                "docker",
            ]),
        ]
