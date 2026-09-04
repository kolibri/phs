from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur_install import AurInstall
from phs.tasks.file_write import FileWrite
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.pacman_update import PacmanUpdate
from phs.tasks.task import Task


@final
class Packages:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            FileWrite(
                Path("/etc/pacman.conf"),
                context.config_templates.render("pacman/pacman.conf.j2"),
                root=True,
                watched=True,
            ),

            PacmanUpdate(),
            PacmanInstall(tuple(data.packages)),
            AurInstall(tuple(data.aur_packages), context.builtin_templates),
        ]
