from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import require_command, require_file
from .ssh import SSHClient


@dataclass(frozen=True, slots=True)
class DiskImage:
    path: Path

    def create(self, size: str) -> None:
        require_command("qemu-img")
        self.path.unlink(missing_ok=True)
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", str(self.path), size],
            check=True,
        )

    def create_overlay(self, backing_file: Path) -> None:
        require_command("qemu-img")
        require_file(backing_file)
        self.path.unlink(missing_ok=True)
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f",
                "qcow2",
                "-F",
                "qcow2",
                "-b",
                str(backing_file.resolve()),
                str(self.path),
            ],
            check=True,
        )


@dataclass(frozen=True, slots=True)
class CloudInitSeed:
    template_dir: Path

    def create(self, directory: Path, *, instance_id: str) -> Path:
        require_command("xorriso")
        directory.mkdir(parents=True, exist_ok=True)

        user_data_template = self.template_dir / "user-data.in"
        meta_data_template = self.template_dir / "meta-data"
        require_file(user_data_template)
        require_file(meta_data_template)

        template = user_data_template.read_text(encoding="utf-8")
        user_data = template.replace("@SSH_PUBLIC_KEY@", SSHClient.public_key())
        meta_data = meta_data_template.read_text(encoding="utf-8")
        meta_data = meta_data.replace("@INSTANCE_ID@", instance_id)

        user_data_path = directory / "user-data"
        meta_data_path = directory / "meta-data"
        iso_path = directory / "cloud-init.iso"

        user_data_path.write_text(user_data, encoding="utf-8")
        meta_data_path.write_text(meta_data, encoding="utf-8")
        iso_path.unlink(missing_ok=True)

        subprocess.run(
            [
                "xorriso",
                "-as",
                "genisoimage",
                "-output",
                str(iso_path),
                "-volid",
                "CIDATA",
                "-joliet",
                "-rock",
                str(user_data_path),
                str(meta_data_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return iso_path
