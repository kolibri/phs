from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur import Aur
from phs.tasks.pacman import Pacman
from phs.tasks.task import Task


@final
class Packages:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            Pacman.update(),
            Pacman.install(data.packages),
            Aur.install(data.aur_packages, context.builtin_templates),
        ]
