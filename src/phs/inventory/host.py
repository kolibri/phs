from pydantic import Field

from phs.inventory.base import InventoryModel
from phs.inventory.config import (
    BackupConfig,
    DesktopConfig,
    FileConfig,
    NfsSource,
    PrinterConfig,
)
from phs.yaml import dump_yaml


class SharedHostConfig(InventoryModel):
    """Collections accepted in both all.yaml and individual host files."""

    packages: list[str] = Field(default_factory=list)
    aur_packages: list[str] = Field(default_factory=list)
    files: list[FileConfig] = Field(default_factory=list)
    nfs_sources: list[NfsSource] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    file_associations: dict[str, str] = Field(default_factory=dict)
    printers: list[PrinterConfig] = Field(default_factory=list)


class AllHostDataFragment(SharedHostConfig):
    username: str
    groupname: str
    homedir: str
    git_user: str
    git_email: str
    shell: str
    modules: list[str] = Field(default_factory=list)


class HostConfig(InventoryModel):
    """Settings that must be specified per host, never in all.yaml."""

    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    desktop: DesktopConfig | None = None
    backup: BackupConfig | None = None


class HostDataFragment(SharedHostConfig, HostConfig):
    username: str | None = None
    groupname: str | None = None
    homedir: str | None = None
    git_user: str | None = None
    git_email: str | None = None
    shell: str | None = None
    modules: list[str] | None = None


class HostData(AllHostDataFragment, HostConfig):
    """Validated, fully resolved configuration with JSON-native serialization."""

    def to_yaml(self) -> str:
        return dump_yaml(self.model_dump(mode="json"))
