import shlex
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.bash import Bash
from phs.tasks.pacman import Pacman
from phs.tasks.service import Service
from phs.tasks.task import Task


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

            Bash.run(
                f"usermod --append --groups docker "
                f"{shlex.quote(data.username)}",
                root=True,
            ),

            Service.enable([
                "docker",
            ]),
        ]