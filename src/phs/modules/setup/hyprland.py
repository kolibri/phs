from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import HostData, HyprlandDesktopConfig
from phs.tasks.copy_path import CopyPath
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.file_write import FileWrite
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class Hyprland:
    config: HyprlandDesktopConfig

    def tasks(
        self,
        context: AppContext,
        data: HostData,
    ) -> list[Task]:
        hypr_dir = Path(data.homedir) / ".config" / "hypr"
        waybar_dir = Path(data.homedir) / ".config" / "waybar"

        tasks: list[Task] = [
            PacmanInstall((
                "hyprland",
                "waybar",
                "hypridle",
                "hyprpaper",
                "hyprlauncher",
                "greetd",
                "polkit",
                "xorg-xwayland",

                "xdg-desktop-portal-hyprland",
                "xdg-desktop-portal-gtk",
            )),
            DirectoryCreate(hypr_dir),
            DirectoryCreate(waybar_dir),

            FileWrite(
                hypr_dir / "hyprland.lua",
                context.config_templates.render(str(self.config.config_file)),
                watched=True,
            ),

            FileWrite(
                hypr_dir / "hyprpaper.conf",
                context.config_templates.render(str(self.config.paper_config_file)),
                watched=True,
            ),

            FileWrite(
                hypr_dir / "hypridle.conf",
                context.config_templates.render(str(self.config.idle_config_file)),
                watched=True,
            ),

            FileWrite(
                waybar_dir / "config.jsonc",
                context.config_templates.render(str(self.config.waybar_config_file)),
                watched=True,
            ),

            FileWrite(
                waybar_dir / "style.css",
                context.config_templates.render(str(self.config.waybar_style_file)),
                watched=True,
            ),


            FileWrite(
                Path("/etc/greetd/config.toml"),
                f"""
                [terminal]
                vt = 1

                [default_session]
                command = "agreety --cmd 'start-hyprland'"
                user = "greeter"

                [initial_session]
                command = "start-hyprland"
                user = "{data.username}"
                """,
                root=True,
                watched=True,
            ),

            ServiceEnable(
                ("greetd",),
                start=False,
            ),
        ]

        wallpaper_source_path = (
            Path(context.settings.config_dir) / "files" / "wallpaper"
        )
        if wallpaper_source_path.is_dir():
            tasks.append(
                CopyPath(
                    wallpaper_source_path,
                    Path(data.homedir) / ".ko" / "wallpaper",
                    create_dirs=True,
                )
            )

        return tasks
