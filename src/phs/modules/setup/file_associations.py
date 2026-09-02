from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.aur import Aur
from phs.tasks.bash import Bash
from phs.tasks.file_association import FileAssociation
from phs.tasks.task import Task


@final
class FileAssociations:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            Bash.run("gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys D89FAAEB4CECAFD199A2F5E612C6F735F7A9A519"),
            Aur.install(["mimeo"], context.builtin_templates),
            FileAssociation.ensure(data.file_associations),
        ]
