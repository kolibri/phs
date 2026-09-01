from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.executor import Executor
from phs.modules.aur import Aur
from phs.modules.copy import Copy
from phs.modules.pacman import Pacman
from phs.modules.task import Task
from phs.target.context import TargetContext
from phs.target.dryrun.dryrun_filesystem import DryRunFilesystem
from phs.target.dryrun.dryrun_runner import DryRunRunner
from phs.target.dryrun.dryrun_transfer import DryRunTransfer
from phs.target.filesystem import Filesystem, RunnerFilesystem
from phs.target.local.local_runner import LocalRunner
from phs.target.local.local_transfer import LocalTransfer
from phs.target.remote.remote_runner import RemoteRunner
from phs.target.remote.remote_transfer import RemoteTransfer
from phs.target.runner import Runner
from phs.target.transfer import Transfer


def init(
        *,
        host: str = 'local',
        dry_run: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    target_host = context.settings.my_hostname if host == 'local' else host
    data = context.inventory.load(target_host)

    runner: Runner
    transfer: Transfer

    if host == 'local':
        local_runner = LocalRunner()
        runner = local_runner
        transfer = LocalTransfer(local_runner)
    else:
        remote_runner = RemoteRunner(
            data.ip,
            data.username,
            port=data.ssh_port,
        )
        runner = remote_runner
        transfer = RemoteTransfer(remote_runner)

    filesystem: Filesystem = RunnerFilesystem(runner)

    target = TargetContext(
        runner=runner,
        filesystem=filesystem,
        transfer=transfer,
    )

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
        target = TargetContext(
            runner=DryRunRunner(runner),
            filesystem=DryRunFilesystem(filesystem),
            transfer=DryRunTransfer(transfer),
        )

    Executor.execute(tasks, target)
