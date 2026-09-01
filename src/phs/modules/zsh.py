from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.copy import Copy
from phs.tasks.task import Task


@final
class Zsh:
    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        return [
            Copy.path(
                context.settings.config_dir / "git",
                # whatever destination you want
                ...
            ),
        ]