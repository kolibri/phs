from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class GitClone:
    repository: str
    destination: Path
    branch: str | None

    def execute(self, target: TargetContext) -> None:
        if target.filesystem.exists(self.destination / ".git"):
            return

        command = [
            "git",
            "clone",
        ]

        if self.branch is not None:
            command.extend([
                "--branch",
                self.branch,
            ])

        command.extend([
            "--",
            self.repository,
            str(self.destination),
        ])

        target.runner.run(command)


@final
class Git:
    @staticmethod
    def clone(
        repository: str,
        destination: Path,
        *,
        branch: str | None = None,
    ) -> Task:
        return GitClone(
            repository=repository,
            destination=destination,
            branch=branch,
        )