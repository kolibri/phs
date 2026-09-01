from textwrap import dedent
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.bash import Bash
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
            Pacman.install(["git","tig","less",]),

            Bash.run(dedent(f"""
                git config --global user.name "{data.git_user}"
                git config --global user.email "{data.git_email}"
                git config --global push.default simple            
                git config --global core.excludesfile {data.homedir}/.gitignore
                git config --global init.defaultBranch main
            """).strip()),
        ]
