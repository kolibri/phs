from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.pacman import Pacman as PacmanTask
from phs.tasks.task import Task


@final
class Pacman:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            PacmanTask.update(),
        ]
