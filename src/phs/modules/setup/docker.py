from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task
from phs.tasks.user_ensure_groups import UserEnsureGroups


@final
class Docker:
    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        return [
            PacmanInstall((
                "docker",
                "docker-buildx",
                "docker-compose",
            )),

            UserEnsureGroups(
                data.username,
                ("docker",),
            ),

            ServiceEnable(("docker",)),
        ]
