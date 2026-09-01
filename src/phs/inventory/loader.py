from pathlib import Path

from pydantic import ValidationError

from phs.inventory.config import FileConfig, NfsSource
from phs.inventory.host import AllHostDataFragment, HostData, HostDataFragment
from phs.yaml import load_yaml


class InventoryError(Exception):
    pass


def format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Invalid configuration: {path}"]
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"])
        if item["type"] == "extra_forbidden":
            lines.append(f"  Unknown key: {location}")
        else:
            lines.append(f"  {location}: {item['msg']}")
    return "\n".join(lines)


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
            hostname=host_config.hostname,
            ip=host_config.ip,
            ssh_port=host_config.ssh_port,
            hdd=host_config.hdd,
            username=host_config.username or all_config.username,
            groupname=host_config.groupname or all_config.groupname,
            homedir=host_config.homedir or all_config.homedir,
            git_user=host_config.git_user or all_config.git_user,
            git_email=host_config.git_email or all_config.git_email,
            shell=host_config.shell or all_config.shell,
            packages=self.merge_unique(all_config.packages, host_config.packages),
            aur_packages=self.merge_unique(all_config.aur_packages, host_config.aur_packages),
            files=self.merge_files(all_config.files, host_config.files),
            nfs_sources=self.merge_nfs_sources(all_config.nfs_sources, host_config.nfs_sources),
            services=self.merge_unique(all_config.services, host_config.services),
            desktop=host_config.desktop,
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

    @staticmethod
    def merge_nfs_sources(
        base: list[NfsSource],
        override: list[NfsSource],
    ) -> list[NfsSource]:
        nfs_sources = {nfs.source: nfs for nfs in base}
        for nfs in override:
            nfs_sources[nfs.source] = nfs
        return list(nfs_sources.values())
