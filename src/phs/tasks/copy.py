from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class CopyPath:
    source: Path
    destination: Path
    root: bool
    create_dirs: bool
    exclude: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        target.transfer.transfer(
            self.source,
            self.destination,
            root=self.root,
            create_dirs=self.create_dirs,
            exclude=self.exclude,
        )


@final
class Copy:
    @staticmethod
    def path(
            source: Path,
            destination: Path,
            *,
            root: bool = False,
            create_dirs: bool = False,
            exclude: list[str] | None = None,
    ) -> Task:
        return CopyPath(
            source=source,
            destination=destination,
            root=root,
            create_dirs=create_dirs,
            exclude=tuple(exclude or ()),
        )
