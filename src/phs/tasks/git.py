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
    update: bool

    def execute(self, target: TargetContext) -> None:
        if target.filesystem.exists(self.destination / ".git"):
            if not self.update:
                return

            target.output.info(f"Updating git repository {self.destination}")
            target.runner.run([
                "git",
                "-C", str(self.destination),
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


@final
@dataclass(frozen=True, slots=True)
class GitConfigEnsure:
    values: tuple[tuple[str, str], ...]

    def execute(self, target: TargetContext) -> None:
        for key, value in self.values:
            result = target.runner.run(
                [
                    "git",
                    "config",
                    "--global",
                    "--get",
                    key,
                ],
                capture_output=True,
                check=False,
            )

            current = (
                result.stdout.strip()
                if result.returncode == 0 and result.stdout is not None
                else None
            )

            if current == value:
                continue

            target.output.info(f"Ensuring git config {key}")
            target.runner.run([
                "git",
                "config",
                "--global",
                key,
                value,
            ])


@final
class Git:
    @staticmethod
    def clone(
        repository: str,
        destination: Path,
        *,
        branch: str | None = None,
        update: bool = False,
    ) -> Task:
        return GitClone(
            repository=repository,
            destination=destination,
            branch=branch,
            update=update,
        )

    @staticmethod
    def config(values: dict[str, str]) -> Task:
        return GitConfigEnsure(
            values=tuple(values.items()),
        )