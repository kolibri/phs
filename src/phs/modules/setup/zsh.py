from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.file_write import FileWrite
from phs.tasks.git_clone import GitClone
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.task import Task


@final
class Zsh:
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        zsh_custom_dir: Path = Path(data.homedir) / ".ko" / "zsh"
        zsh_plugins: list[str] = ["git"]

        return [
            PacmanInstall(("git", "tig", "less")),

            GitClone("https://github.com/ohmyzsh/ohmyzsh.git", Path(data.homedir) / ".oh-my-zsh", update=True),
            DirectoryCreate(zsh_custom_dir),
            FileWrite(
                Path(data.homedir) / ".zshrc",
                context.config_templates.render(
                    "zsh/zshrc.j2",
                    zsh_custom_dir=str(zsh_custom_dir),
                    zsh_plugins=" ".join(zsh_plugins)
                ),
                watched=True,
            ),
            FileWrite(
                zsh_custom_dir / "ko.zsh-theme",
                context.config_templates.render("zsh/ko.zsh-theme.j2"),
                watched=True,
            ),
            FileWrite(
                zsh_custom_dir / "ko_functions.zsh",
                context.config_templates.render("zsh/ko_functions.zsh.j2"),
                watched=True,
            )

        ]
