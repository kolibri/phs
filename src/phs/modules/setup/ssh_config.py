from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.ssh_config_ensure import SshConfigEnsure
from phs.tasks.task import Task


@final
class SshConfig:
    def tasks(self, context: AppContext, data: HostData) -> list[Task]:
        return [SshConfigEnsure(Path(data.homedir), tuple(data.ssh_config.items()))]
