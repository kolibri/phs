from typing import final

from phs.context import AppContext
from phs.inventory import DesktopConfig, QtileDesktopConfig, GnomeDesktopConfig, HostData
from phs.modules.base import Module
from phs.modules.setup.gnome import Gnome
from phs.modules.setup.qtile import Qtile
from phs.tasks.task import Task


@final
class DesktopFactory:
    @staticmethod
    def create(
        config: DesktopConfig,
    ) -> list[Module]:
        if isinstance(config, QtileDesktopConfig):
            return [Qtile(config)]

        if isinstance(config, GnomeDesktopConfig):
            return [Gnome()]

        raise TypeError(
            f"Unsupported desktop config: {type(config)}"
        )


@final
class Desktop:
    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        if data.desktop is None:
            return []

        context.output.info(f"[bold]Desktop is set to {data.desktop.type}[/bold]")
        tasks: list[Task] = []

        for module in DesktopFactory.create(data.desktop):
            tasks.extend(
                module.tasks(
                    context,
                    data,
                )
            )

        return tasks
