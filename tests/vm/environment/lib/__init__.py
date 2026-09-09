from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import NoReturn


def log(message: str) -> None:
    print()
    print(f"TEST>>> {message} <<<", flush=True)


def die(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        die(f"required command not found: {name}")


def require_file(path: Path) -> None:
    if not path.is_file():
        die(f"required file does not exist: {path}")


def ensure_directories(*directories: Path) -> None:
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def check_kvm_access() -> None:
    kvm = Path("/dev/kvm")
    if kvm.exists() and not os.access(kvm, os.R_OK | os.W_OK):
        die("/dev/kvm exists but is not accessible to the current user")
