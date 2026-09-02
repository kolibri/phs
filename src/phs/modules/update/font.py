from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.fnt import Fnt
from phs.tasks.task import Task


@final
class Font:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        if not data.fonts:
            return []

        return [
            Fnt.update(),
            Fnt.install(data.fonts),
        ]
