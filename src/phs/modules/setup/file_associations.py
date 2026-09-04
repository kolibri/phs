from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur_install import AurInstall
from phs.tasks.bash_run import BashRun
from phs.tasks.file_association_ensure import FileAssociationEnsure
from phs.tasks.task import Task


@final
class FileAssociations:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            BashRun("gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys D89FAAEB4CECAFD199A2F5E612C6F735F7A9A519"),
            AurInstall(("mimeo",), context.builtin_templates),
            FileAssociationEnsure(tuple(data.file_associations.items())),
        ]
