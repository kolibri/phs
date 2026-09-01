from pathlib import Path
from typing import final, override

from phs.target.filesystem import Filesystem


@final
class DryRunFilesystem(Filesystem):
    filesystem: Filesystem

    def __init__(self, filesystem: Filesystem) -> None:
        self.filesystem = filesystem

    @property
    @override
    def description(self) -> str:
        return self.filesystem.description

    @override
    def exists(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> bool:
        return self.filesystem.exists(
            path,
            root=root,
        )

    @override
    def read_text(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> str:
        return self.filesystem.read_text(
            path,
            root=root,
        )

    @override
    def write_text(
        self,
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> None:
        prefix = "sudo " if root else ""

        print(
            f"[dry-run] [{self.filesystem.description}] "
            f"{prefix}write {path}"
        )
