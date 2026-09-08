from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from phs.inventory.base import InventoryModel


class FileConfig(InventoryModel):
    target: Path
    src: Path
    root: bool = False


class NfsSource(InventoryModel):
    source: str
    target: Path
    options: str


class HyprlandDesktopConfig(InventoryModel):
    type: Literal["hyprland"]
    hypr_dir: Path
    waybar_dir: Path


class QtileDesktopConfig(InventoryModel):
    type: Literal["qtile"]
    config_file: Path


class GnomeDesktopConfig(InventoryModel):
    type: Literal["gnome"]


type DesktopConfig = Annotated[
    HyprlandDesktopConfig | QtileDesktopConfig | GnomeDesktopConfig,
    Field(discriminator="type"),
]


class PrinterConfig(InventoryModel):
    name: str
    uri: str
    default: bool = False


class BackupConfig(InventoryModel):
    manifest_path: Path
    include: list[Path] = Field(min_length=1)
    excludes: list[str] = Field(default_factory=list)
    target_dir: Path
