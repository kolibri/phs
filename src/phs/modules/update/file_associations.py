from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.file_association import FileAssociation
from phs.tasks.task import Task


@final
class FileAssociations:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        if not data.file_associations:
            return []

        return [
            FileAssociation.ensure(data.file_associations),
        ]
