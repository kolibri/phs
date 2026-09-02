from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur import Aur
from phs.tasks.fnt import Fnt
from phs.tasks.task import Task


@final
class Font:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            Aur.install(["fnt"], context.builtin_templates),
            Fnt.update(),
            Fnt.install(data.fonts),
        ]
