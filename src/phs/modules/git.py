from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.copy import Copy
from phs.tasks.task import Task


@final
class Git:
    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        print("git stuff")
        return []