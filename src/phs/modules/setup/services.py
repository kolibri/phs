from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task


@final
class Services:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            ServiceEnable(tuple(data.services)),
        ]
