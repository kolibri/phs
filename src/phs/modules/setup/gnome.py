from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task


@final
class Gnome:
    def tasks(
        self,
        _context: AppContext,
        _data: HostData,
    ) -> list[Task]:
        return [
            PacmanInstall((
                "gdm",
                "gnome-control-center",
            )),

            ServiceEnable(("gdm",)),
        ]
