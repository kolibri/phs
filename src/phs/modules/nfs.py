import re
from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.bash import Bash
from phs.tasks.directory import Directory
from phs.tasks.file import File
from phs.tasks.modprobe import Modprobe
from phs.tasks.mount import Mount
from phs.tasks.pacman import Pacman
from phs.tasks.service import Service
from phs.tasks.task import Task


@final
class Nfs:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        tasks: list[Task] = [
            Pacman.install(['nfs-utils']),
            Modprobe.load(['nfsd']),
            #Service.enable('rpcbind') #todo: check, if needed
        ]

        for nfs in data.nfs_sources:
            tasks.extend([
                Directory.create(nfs.target, root=True),
                File.ensure_line(
                    Path("/etc/fstab"),
                    line=f"{nfs.source} {str(nfs.target)} {nfs.options}",
                    match=rf"^{re.escape(nfs.source)}(?:\s|$)",
                    root=True,
                ),
            ])

        tasks.append(Bash.run("systemctl daemon-reload", root=True))

        for nfs in data.nfs_sources:
            tasks.append(Mount.ensure(nfs.target))

        return tasks
