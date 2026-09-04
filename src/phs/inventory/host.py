from typing import ClassVar, TypedDict

from attr import dataclass
from pydantic import BaseModel, ConfigDict, Field

from phs.inventory.config import (
    DesktopConfig,
    DesktopConfigDict,
    FileConfig,
    FileConfigDict,
    NfsSource,
    NfsSourceDict,
    desktop_to_dict,
    file_config_to_dict,
    nfs_source_to_dict, BackupConfig, backup_config_to_dict, BackupConfigDict,
)
from phs.yaml import dump_yaml


class AllHostDataFragment(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    username: str
    groupname: str
    homedir: str
    git_user: str
    git_email: str
    shell: str
    modules: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    aur_packages: list[str] = Field(default_factory=list)
    files: list[FileConfig] = Field(default_factory=list)
    nfs_sources: list[NfsSource] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    file_associations: dict[str, str] = Field(default_factory=dict)
    backup: BackupConfig | None = None


class HostDataFragment(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str | None = None
    groupname: str | None = None
    homedir: str | None = None
    git_user: str | None = None
    git_email: str | None = None
    shell: str | None = None
    modules: list[str] | None = None
    packages: list[str] = Field(default_factory=list)
    aur_packages: list[str] = Field(default_factory=list)
    files: list[FileConfig] = Field(default_factory=list)
    nfs_sources: list[NfsSource] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    file_associations: dict[str, str] = Field(default_factory=dict)
    desktop: DesktopConfig | None = None
    backup: BackupConfig | None = None



class HostDataDict(TypedDict):
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str
    groupname: str
    homedir: str
    git_user: str
    git_email: str
    shell: str
    modules: list[str]
    packages: list[str]
    aur_packages: list[str]
    files: list[FileConfigDict]
    nfs_sources: list[NfsSourceDict]
    services: list[str]
    fonts: list[str]
    file_associations: dict[str, str]
    desktop: DesktopConfigDict | None
    backup: BackupConfigDict | None



@dataclass
class HostData:
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str
    groupname: str
    homedir: str
    git_user: str
    git_email: str
    shell: str
    modules: list[str]
    packages: list[str]
    aur_packages: list[str]
    files: list[FileConfig]
    nfs_sources: list[NfsSource]
    services: list[str]
    fonts: list[str]
    file_associations: dict[str, str]
    desktop: DesktopConfig | None
    backup: BackupConfig | None


    def to_dict(self) -> HostDataDict:
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "ssh_port": self.ssh_port,
            "hdd": self.hdd,
            "username": self.username,
            "groupname": self.groupname,
            "homedir": self.homedir,
            "git_user": self.git_user,
            "git_email": self.git_email,
            "shell": self.shell,
            "modules": self.modules,
            "packages": self.packages,
            "aur_packages": self.aur_packages,
            "files": [
                file_config_to_dict(file)
                for file in self.files
            ],
            "nfs_sources": [
                nfs_source_to_dict(nfs)
                for nfs in self.nfs_sources
            ],
            "services": self.services,
            "fonts": self.fonts,
            "file_associations": self.file_associations,
            "desktop": desktop_to_dict(self.desktop),
            "backup": backup_config_to_dict(self.backup),
        }

    def to_yaml(self) -> str:
        return dump_yaml(self.to_dict())
