from dataclasses import dataclass
from typing import final

from phs.backup.base import BackupRsyncData, create_rsync_backup_command
from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BackupSnapshotCreate:
    rsync: BackupRsyncData

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Backing up {self.rsync.source_dir} to {self.rsync.destination_dir}")

        partial = self.rsync.destination_dir.with_name(f".{self.rsync.destination_dir.name}.partial")

        target.runner.run(
            ["mkdir", "--", str(partial)],
            root=True,
        )

        target.runner.run(
            create_rsync_backup_command(
                manifest=self.rsync.manifest_path,
                source=self.rsync.source_dir,
                destination=self.rsync.partial_dir,
                previous=self.rsync.previous_dir,
            ),
            root=True,
        )

        target.runner.run(
            ["mv", "--", str(partial), str(self.rsync.destination_dir)],
            root=True,
        )
