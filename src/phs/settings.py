from dataclasses import dataclass
from pathlib import Path
import socket
from cyclopts import Parameter


@Parameter(name="*")
@dataclass(frozen=True, slots=True)
class Settings:
    config_dir: Path = Path(Path.home() / ".phs" / "hosts")
    sshkey: Path = Path.home() / ".ssh" / "id_rsa.pub"
    my_hostname: str = socket.gethostname()
