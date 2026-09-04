from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class GitClone:
    repository: str
    destination: Path
    branch: str | None = None
    update: bool = False

    def execute(self, target: TargetContext) -> None:
        if target.filesystem.exists(self.destination / ".git"):
            if not self.update:
                return

            target.output.info(f"Updating git repository {self.destination}")
            target.runner.run([
                "git",
                "-C",
                str(self.destination),
                "pull",
                "--ff-only",
            ])
            return

        target.output.info(f"Cloning git repository {self.repository}")

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
