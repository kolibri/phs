from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.git_config_ensure import GitConfigEnsure
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.task import Task


@final
class Git:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        return [
            PacmanInstall((
                "git",
                "tig",
                "less",
            )),

            GitConfigEnsure(tuple({
                "user.name": data.git_user,
                "user.email": data.git_email,
                "push.default": "simple",
                "core.excludesfile": f"{data.homedir}/.gitignore",
                "init.defaultBranch": "main",
            }.items())),
        ]
