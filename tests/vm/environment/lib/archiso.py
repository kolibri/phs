from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import die, ensure_directories, log


@dataclass(frozen=True, slots=True)
class JsonFile:
    path: Path

    def read(self) -> dict[str, object]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError, json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    def write(self, value: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


@dataclass(frozen=True, slots=True)
class Sha256:
    value: str

    @classmethod
    def from_file(cls, path: Path) -> Sha256:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(4 * 1024 * 1024):
                digest.update(chunk)
        return cls(digest.hexdigest())

    @classmethod
    def from_text(cls, value: str) -> Sha256:
        return cls(hashlib.sha256(value.encode()).hexdigest())

    def matches_file(self, path: Path) -> bool:
        return Sha256.from_file(path) == self

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ArchIso:
    url: str
    sha256_url: str
    path: Path
    metadata: JsonFile
    environment_directories: tuple[Path, ...]

    def current_sha256(self) -> Sha256:
        with urllib.request.urlopen(self.sha256_url, timeout=30) as response:
            content = response.read().decode("utf-8")

        for line in content.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[-1].lstrip("*") == self.path.name:
                checksum = fields[0].lower()
                if re.fullmatch(r"[0-9a-f]{64}", checksum):
                    return Sha256(checksum)

        die(f"could not find {self.path.name} in {self.sha256_url}")

    def ensure_current(self, *, force: bool = False) -> None:
        ensure_directories(*self.environment_directories)
        log("checking current Arch ISO")

        expected = self.current_sha256()
        if self.path.is_file() and not force and expected.matches_file(self.path):
            self.metadata.write(
                {"sha256": str(expected), "size": self.path.stat().st_size}
            )
            print(f"Arch ISO is current: {self.path}")
            return

        temporary = self.path.with_suffix(".iso.part")
        temporary.unlink(missing_ok=True)

        log("downloading current Arch ISO")
        digest = hashlib.sha256()
        downloaded = 0

        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": "phs-vm-tests/1"},
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                total_header = response.headers.get("Content-Length")
                total = (
                    int(total_header)
                    if total_header and total_header.isdigit()
                    else None
                )
                next_report = 128 * 1024 * 1024

                with temporary.open("wb") as destination:
                    while chunk := response.read(1024 * 1024):
                        destination.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)

                        if downloaded >= next_report:
                            if total:
                                percent = downloaded * 100 / total
                                print(
                                    f"Downloaded {downloaded // (1024 * 1024)} MiB "
                                    f"({percent:.1f}%)",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"Downloaded {downloaded // (1024 * 1024)} MiB",
                                    flush=True,
                                )
                            next_report += 128 * 1024 * 1024
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

        actual = Sha256(digest.hexdigest())
        if actual != expected:
            temporary.unlink(missing_ok=True)
            die(f"Arch ISO checksum mismatch: expected {expected}, got {actual}")

        temporary.replace(self.path)
        self.metadata.write({"sha256": str(expected), "size": downloaded})
        print(f"Arch ISO ready: {self.path}")

    def sha256(self) -> Sha256:
        value = self.metadata.read().get("sha256")
        if not isinstance(value, str):
            die("Arch ISO metadata is missing; run download-archiso")
        return Sha256(value)
