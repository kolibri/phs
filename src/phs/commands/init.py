from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.executor import Executor
from phs.modules.aur import Aur
from phs.modules.copy import Copy
from phs.modules.pacman import Pacman
from phs.modules.task import Task
from phs.target.base import Target
from phs.target.dryrun import DryRunTarget
from phs.target.local import LocalTarget
from phs.target.remote import RemoteTarget


def init(
        *,
        host: str = 'local',
        dry_run: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    target_host = context.settings.my_hostname if host == 'local' else host
    data = context.inventory.load(target_host)

    target = LocalTarget() if host == 'local' else RemoteTarget(data.ip, data.username, port=data.ssh_port)


    print("init system")

    tasks: list[Task] = [
        Pacman.update(),
        Pacman.install(data.packages),
        Copy.path(
            Path.cwd(),
            Path(data.homedir) / "projects" / "phs",
            create_dirs=True,
            exclude=[
                "test/qemu/iso",
                "test/qemu/state",
                ".idea",
                ".venv",
                "__pycache__",
            ],
        )
#        Aur.install(data.aur_packages, context.builtin_templates),
    ]

    if dry_run:
        target = DryRunTarget(target)


    Executor.execute(tasks, target)