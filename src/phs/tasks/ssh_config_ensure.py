from dataclasses import dataclass
from pathlib import Path
from typing import final

from pydantic import TypeAdapter

from phs.inventory.config import SshHostConfig
from phs.ssh_config import ensure_ssh_include, render_ssh_config
from phs.target.context import TargetContext
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.file_write import FileWrite


@final
@dataclass(frozen=True, slots=True)
class SshConfigEnsure:
    home: Path
    hosts: tuple[tuple[str, SshHostConfig], ...]

    def execute(self, target: TargetContext) -> None:
        if not self.home.is_absolute() or ".." in self.home.parts:
            raise ValueError(
                "SSH configuration requires an absolute managed home directory without '..'"
            )
        if len(dict(self.hosts)) != len(self.hosts):
            raise ValueError("Duplicate SSH Host entries")
        hosts = TypeAdapter(dict[str, SshHostConfig]).validate_python(dict(self.hosts))
        content = render_ssh_config(hosts)
        ssh_dir = self.home / ".ssh"
        config = ssh_dir / "config"
        managed_dir = ssh_dir / "config.d"
        managed = managed_dir / "phs"
        actual = (
            target.filesystem.read_text(config)
            if target.filesystem.exists(config)
            else ""
        )
        updated = ensure_ssh_include(actual, self.home)

        for directory in (ssh_dir, managed_dir):
            DirectoryCreate(directory).execute(target)
            target.filesystem.ensure_mode(directory, 0o700)
        FileWrite(managed, content, as_given=True).execute(target)
        target.filesystem.ensure_mode(managed, 0o600)
        if updated != actual:
            target.filesystem.write_text(config, updated)
        target.filesystem.ensure_mode(config, 0o600)
