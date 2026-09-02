from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.service import Service
from phs.tasks.task import Task


@final
class Services:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            Service.enable(data.services),
        ]
