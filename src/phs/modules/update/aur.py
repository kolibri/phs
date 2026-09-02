from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur import Aur as AurTask
from phs.tasks.task import Task


@final
class Aur:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            AurTask.install(
                data.aur_packages,
                context.builtin_templates,
            ),
        ]
