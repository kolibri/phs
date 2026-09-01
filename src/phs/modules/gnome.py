from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.pacman import Pacman
from phs.tasks.service import Service
from phs.tasks.task import Task


@final
class Gnome:
    def tasks(
        self,
        _context: AppContext,
        _data: HostData,
    ) -> list[Task]:
        return [
            Pacman.install([
                "gdm",
                "gnome-control-center",
            ]),

            Service.enable([
                "gdm",
            ]),
        ]