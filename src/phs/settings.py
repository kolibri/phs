import socket
from dataclasses import dataclass
from pathlib import Path

from cyclopts import Parameter


@Parameter(name="*")
@dataclass(frozen=True, slots=True)
class Settings:
    config_dir: Path = Path(Path.home() / ".phs" / "hosts")
    sshkey: Path = Path.home() / ".ssh" / "id_ed25519.pub"
    my_hostname: str = socket.gethostname()
    loose_ssh: bool = False
    installer_iso_url: str = (
        "https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso"
    )
