from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur_install import AurInstall
from phs.tasks.file_write import FileWrite
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.pacman_update import PacmanUpdate
from phs.tasks.printer_ensure import PrinterEnsure
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task


@final
class Printer:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        tasks: list[Task] = [
            PacmanInstall(("cups", "avahi")),
            ServiceEnable((
                "cups.service",
                "avahi-daemon.service"
            )),
        ]

        for printer in data.printers:
            tasks.append(
                PrinterEnsure(
                    name=printer.name,
                    uri=printer.uri,
                    default=printer.default,
                )

            )

        return tasks