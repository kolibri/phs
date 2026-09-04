from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class UserEnsureGroups:
    username: str
    groups: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        result = target.runner.run(
            ["id", "--name", "--groups", self.username],
            capture_output=True,
        )
        current_groups = set((result.stdout or "").split())
        missing_groups = [
            group
            for group in self.groups
            if group not in current_groups
        ]

        if not missing_groups:
            return

        target.output.info(
            f'Adding {self.username} to groups {" ".join(missing_groups)}'
        )
        target.runner.run(
            [
                "usermod",
                "--append",
                "--groups",
                ",".join(missing_groups),
                self.username,
            ],
            root=True,
        )
