from dataclasses import dataclass
from typing import final

from phs.backup.base import BackupRsync
from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BackupSnapshotCreate:
    rsync: BackupRsync

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Backing up {self.rsync.source} to {self.rsync.destination}")

        partial = self.rsync.destination.with_name(f".{self.rsync.destination.name}.partial")

        target.runner.run(
            ["mkdir", "--", str(partial)],
            root=True,
        )

        target.runner.run(
            self.rsync.command(),
            root=True,
        )

        target.runner.run(
            ["mv", "--", str(partial), str(self.destination)],
            root=True,
        )
