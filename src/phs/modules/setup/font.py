from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur_install import AurInstall
from phs.tasks.fnt_install import FntInstall
from phs.tasks.fnt_update import FntUpdate
from phs.tasks.task import Task


@final
class Font:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            AurInstall(("fnt",), context.builtin_templates),
            FntUpdate(),
            FntInstall(tuple(data.fonts)),
        ]
