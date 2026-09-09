from __future__ import annotations

import os
import shlex
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TextIO

from . import die, log, require_file


@dataclass(frozen=True, slots=True)
class SSHClient:
    port: int
    user: str
    host: str = "127.0.0.1"
    availability_timeout: float = 300.0

    @staticmethod
    def private_key() -> Path:
        configured = os.environ.get("PHS_VM_SSH_KEY")
        if configured:
            path = Path(configured).expanduser()
            require_file(path)
            require_file(Path(f"{path}.pub"))
            return path

        for candidate in (
            Path.home() / ".ssh" / "id_ed25519",
            Path.home() / ".ssh" / "id_rsa",
        ):
            if candidate.is_file() and Path(f"{candidate}.pub").is_file():
                return candidate

        die("no SSH key found; set PHS_VM_SSH_KEY")

    @classmethod
    def public_key(cls) -> str:
        return Path(f"{cls.private_key()}.pub").read_text(encoding="utf-8").strip()

    def base_command(self) -> list[str]:
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=2",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            str(self.private_key()),
            "-p",
            str(self.port),
        ]

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = True,
        capture_output: bool = False,
        input_text: str | None = None,
        stdin: BinaryIO | TextIO | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if not command:
            raise ValueError("remote command must not be empty")
        if input_text is not None and stdin is not None:
            raise ValueError("input_text and stdin are mutually exclusive")

        return subprocess.run(
            [*self.base_command(), f"{self.user}@{self.host}", shlex.join(command)],
            check=check,
            capture_output=capture_output,
            input=input_text,
            stdin=stdin,
            text=True,
        )

    def interactive(self) -> None:
        subprocess.run(
            [*self.base_command(), f"{self.user}@{self.host}"],
            check=True,
        )

    def wait_until_available(self, description: str) -> None:
        log(f"waiting for {description} SSH")
        deadline = time.monotonic() + self.availability_timeout

        while time.monotonic() < deadline:
            result = self.run(["true"], check=False, capture_output=True)
            if result.returncode == 0:
                print(f"{description} SSH is available")
                return
            print(".", end="", flush=True)
            time.sleep(0.25)

        print()
        die(
            f"{description} SSH did not become available "
            f"within {self.availability_timeout:.0f}s"
        )
