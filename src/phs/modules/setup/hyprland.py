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
        hypr_target_dir = Path(data.homedir) / ".config" / "hypr"
        waybar_target_dir = Path(data.homedir) / ".config" / "waybar"

        hypr_source_dir = Path(context.settings.config_dir) / "files" / data.desktop.hypr_dir
        waybar_source_dir = Path(context.settings.config_dir) / "files" / data.desktop.waybar_dir


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
            DirectoryCreate(hypr_target_dir),
            DirectoryCreate(waybar_target_dir),

            CopyPath(hypr_source_dir, hypr_target_dir),
            CopyPath(waybar_source_dir, waybar_target_dir),

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
