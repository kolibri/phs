from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.tasks.directory import Directory
from phs.tasks.file import File
from phs.tasks.git import Git
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
            Git.clone("https://github.com/ohmyzsh/ohmyzsh.git", Path(data.homedir) / ".oh-my-zsh"),
            Directory.create(zsh_custom_dir),
            File.write(
                Path(data.homedir) / ".zshrc",
                context.config_templates.render(
                    "zsh/zshrc.j2",
                    zsh_custom_dir=str(zsh_custom_dir),
                    zsh_plugins=" ".join(zsh_plugins)
                )
            ),
            File.write(
                zsh_custom_dir / "ko.zsh-theme",
                context.config_templates.render("zsh/ko.zsh-theme.j2")
            ),
            File.write(
                zsh_custom_dir / "ko_functions.zsh",
                context.config_templates.render("zsh/ko_functions.zsh.j2")
            )

        ]
