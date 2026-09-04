from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.context import AppContext
from phs.inventory import QtileDesktopConfig, HostData
from phs.tasks.copy_path import CopyPath
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.file_write import FileWrite
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class Qtile:
    config: QtileDesktopConfig

    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> list[Task]:
        config_dir = (Path(data.homedir) / ".config" / "qtile")
        environment_dir = (Path(data.homedir) / ".config" / "environment.d")
        portal_dir = (Path(data.homedir) / ".config" / "xdg-desktop-portal")

        tasks: list[Task] = [
            PacmanInstall((
                "qtile",
                "greetd",
                "polkit",
                "wlopm",
                "xorg-xwayland",
                "xdg-desktop-portal-wlr",
                "xdg-desktop-portal-gtk",
            )),

            DirectoryCreate(environment_dir),
            DirectoryCreate(portal_dir),
            DirectoryCreate(config_dir),

            FileWrite(
                environment_dir / "qtile.conf",
                """
                XDG_SESSION_TYPE=wayland
                XDG_SESSION_DESKTOP=qtile
                XDG_CURRENT_DESKTOP=qtile
                DESKTOP_SESSION=qtile
                """,
                watched=True,
            ),

            FileWrite(
                Path("/etc/greetd/config.toml"),
                f"""
                [terminal]
                vt = 1
        
                [default_session]
                command = "agreety --cmd 'systemctl --user start --wait qtile.service'"
                user = "greeter"
        
                [initial_session]
                command = "systemctl --user start --wait qtile.service"
                user = "{data.username}"
                """,
                root=True,
                watched=True,
            ),

            FileWrite(
                config_dir / "config.py",
                context.config_templates.render(str(self.config.config_file)),
                watched=True,
            ),

            FileWrite(
                portal_dir / "qtile-portals.conf",
                """
                [preferred]
                default=wlr;gtk
                """,
                watched=True,
            ),
            ServiceEnable(
                ("greetd",),
                start=False,
            ),
        ]

        wallpaper_source_path = Path(context.settings.config_dir) / "files" / "wallpaper"
        if wallpaper_source_path.is_dir():
            tasks.append(CopyPath(
                wallpaper_source_path,
                Path(data.homedir) / ".ko" / "wallpaper",
                create_dirs=True,
            ))

        return tasks
