from pathlib import Path
from typing import ClassVar, TypedDict

from attr import dataclass
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from phs.yaml import dump_yaml, load_yaml


def format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Invalid configuration: {path}"]
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"])
        if item["type"] == "extra_forbidden":
            lines.append(f"  Unknown key: {location}")
        else:
            lines.append(f"  {location}: {item['msg']}")
    return "\n".join(lines)


class InventoryError(Exception):
    pass


class FileConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    target: Path
    src: Path
    root: bool = False


class AllHostDataFragment(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str
    groupname: str
    git_user: str
    git_email: str
    shell: str
    packages: list[str] = Field(default_factory=list)
    aur_packages: list[str] = Field(default_factory=list)
    files: list[FileConfig] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class HostDataFragment(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    hostname: str | None = None
    ip: str | None = None
    ssh_port: int | None = None
    hdd: str | None = None
    username: str | None = None
    groupname: str | None = None
    git_user: str | None = None
    git_email: str | None = None
    shell: str | None = None
    packages: list[str] = Field(default_factory=list)
    aur_packages: list[str] = Field(default_factory=list)
    files: list[FileConfig] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class FileConfigDict(TypedDict):
    target: str
    src: str
    root: bool


class HostDataDict(TypedDict):
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str
    groupname: str
    git_user: str
    git_email: str
    shell: str
    packages: list[str]
    aur_packages: list[str]
    files: list[FileConfigDict]
    services: list[str]


@dataclass
class HostData:
    hostname: str
    ip: str
    ssh_port: int
    hdd: str
    username: str
    groupname: str
    git_user: str
    git_email: str
    shell: str
    packages: list[str]
    aur_packages: list[str]
    files: list[FileConfig]
    services: list[str]

    def to_dict(self) -> HostDataDict:
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "ssh_port": self.ssh_port,
            "hdd": self.hdd,
            "username": self.username,
            "groupname": self.groupname,
            "git_user": self.git_user,
            "git_email": self.git_email,
            "shell": self.shell,
            "packages": self.packages,
            "aur_packages": self.aur_packages,
            "files": [
                {
                    "target": str(file.target),
                    "src": str(file.src),
                    "root": file.root,
                }
                for file in self.files
            ],
            "services": self.services,
        }

    def to_yaml(self) -> str:
        return dump_yaml(self.to_dict())


class HostDataLoader:
    def __init__(self, config_dir: Path):
        self.config_dir: Path = config_dir

    def load(self, hostname: str) -> HostData:
        path = self.config_dir / "all.yaml"
        try:
            all_config = AllHostDataFragment.model_validate(
                load_yaml(self.config_dir / "all.yaml")
            )
            host_config = HostDataFragment.model_validate(
                load_yaml(self.config_dir / f"{hostname}.yaml")
            )
        except ValidationError as error:
            raise InventoryError(
                format_validation_error(path, error)
            ) from error

        return HostData(
            hostname=host_config.hostname or all_config.hostname,
            ip=host_config.ip or all_config.ip,
            ssh_port=host_config.ssh_port or all_config.ssh_port,
            hdd=host_config.hdd or all_config.hdd,
            username=host_config.username or all_config.username,
            groupname=host_config.groupname or all_config.groupname,
            git_user=host_config.git_user or all_config.git_user,
            git_email=host_config.git_email or all_config.git_email,
            shell=host_config.shell or all_config.shell,
            packages=self.merge_unique(all_config.packages, host_config.packages),
            aur_packages=self.merge_unique(all_config.aur_packages, host_config.aur_packages),
            files=self.merge_files(all_config.files, host_config.files),
            services=self.merge_unique(all_config.services, host_config.services),
        )

    @staticmethod
    def merge_unique(base: list[str], override: list[str]) -> list[str]:
        return list(dict.fromkeys(base + override))

    @staticmethod
    def merge_files(
            base: list[FileConfig],
            override: list[FileConfig],
    ) -> list[FileConfig]:
        files = {file.target: file for file in base}
        for file in override:
            files[file.target] = file
        return list(files.values())
