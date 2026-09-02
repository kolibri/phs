from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class DirectoryCreate:
    path: Path
    root: bool

    def execute(self, target: TargetContext) -> None:
        target.output.info(f'Ensuring directory {str(self.path)}')

        target.runner.run(
            [
                "mkdir",
                "-p",
                "--",
                str(self.path),
            ],
            root=self.root,
        )


@final
class Directory:
    @staticmethod
    def create(
        path: Path,
        *,
        root: bool = False,
    ) -> Task:
        return DirectoryCreate(
            path=path,
            root=root,
        )