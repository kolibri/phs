from pathlib import Path
from typing import Annotated, ClassVar, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class FileConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    target: Path
    src: Path
    root: bool = False


class FileConfigDict(TypedDict):
    target: str
    src: str
    root: bool


def file_config_to_dict(file: FileConfig) -> FileConfigDict:
    result: FileConfigDict = {
        "target": str(file.target),
        "src": str(file.src),
        "root": file.root,
    }
    return result


class NfsSource(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    source: str
    target: Path
    options: str


class NfsSourceDict(TypedDict):
    source: str
    target: str
    options: str


def nfs_source_to_dict(nfs: NfsSource) -> NfsSourceDict:
    result: NfsSourceDict = {
        "source": nfs.source,
        "target": str(nfs.target),
        "options": nfs.options,
    }
    return result


class QtileDesktopConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    type: Literal["qtile"]
    config_file: Path


class GnomeDesktopConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    type: Literal["gnome"]


type DesktopConfig = Annotated[
    QtileDesktopConfig | GnomeDesktopConfig,
    Field(discriminator="type"),
]


class QtileDesktopConfigDict(TypedDict):
    type: Literal["qtile"]
    config_file: str


class GnomeDesktopConfigDict(TypedDict):
    type: Literal["gnome"]


type DesktopConfigDict = (
    QtileDesktopConfigDict
    | GnomeDesktopConfigDict
)


def desktop_to_dict(
    desktop: DesktopConfig | None,
) -> DesktopConfigDict | None:
    if isinstance(desktop, QtileDesktopConfig):
        result: QtileDesktopConfigDict = {
            "type": "qtile",
            "config_file": str(desktop.config_file),
        }
        return result

    if isinstance(desktop, GnomeDesktopConfig):
        result: GnomeDesktopConfigDict = {
            "type": "gnome",
        }
        return result

    return None
