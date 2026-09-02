from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.git import Git as GitTask
from phs.tasks.pacman import Pacman
from phs.tasks.task import Task


@final
class Git:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            Pacman.install([
                "git",
                "tig",
                "less",
            ]),

            GitTask.config({
                "user.name": data.git_user,
                "user.email": data.git_email,
                "push.default": "simple",
                "core.excludesfile": f"{data.homedir}/.gitignore",
                "init.defaultBranch": "main",
            }),
        ]