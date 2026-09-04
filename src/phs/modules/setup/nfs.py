import re
from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.ensure_line import EnsureLine
from phs.tasks.modprobe_load import ModprobeLoad
from phs.tasks.mount_ensure import MountEnsure
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_daemon_reload import ServiceDaemonReload
from phs.tasks.task import Task


@final
class Nfs:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        tasks: list[Task] = [
            PacmanInstall(("nfs-utils",)),
            ModprobeLoad(("nfsd",)),
            # ServiceEnable(("rpcbind",))  # TODO: check if needed
        ]

        for nfs in data.nfs_sources:
            tasks.extend([
                DirectoryCreate(nfs.target, root=True),
                EnsureLine(
                    Path("/etc/fstab"),
                    line=f"{nfs.source} {str(nfs.target)} {nfs.options}",
                    match=rf"^{re.escape(nfs.source)}(?:\s|$)",
                    root=True,
                ),
            ])

        tasks.append(ServiceDaemonReload())

        for nfs in data.nfs_sources:
            tasks.append(MountEnsure(nfs.target))

        return tasks
