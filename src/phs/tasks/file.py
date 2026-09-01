from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class FileWrite:
    path: Path
    content: str
    root: bool

    def execute(self, target: TargetContext) -> None:
        target.filesystem.write_text(
            self.path,
            self.content,
            root=self.root,
        )


@final
class File:
    @staticmethod
    def write(
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> Task:
        return FileWrite(
            path=path,
            content=content,
            root=root,
        )