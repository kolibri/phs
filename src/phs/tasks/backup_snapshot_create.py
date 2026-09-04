from dataclasses import dataclass
from typing import final

from phs.backup.base import (
    BackupRsyncData,
    BackupSnapshotError,
    create_rsync_backup_command,
)
from phs.target.base import TargetCommandError
from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BackupSnapshotCreate:
    rsync: BackupRsyncData
    user: str
    group: str

    def execute(self, target: TargetContext) -> None:
        target.output.info(
            f"Backing up {self.rsync.source_dir} "
            f"to {self.rsync.destination_dir}"
        )

        target.runner.run(
            [
                "install",
                "-d",
                "-o",
                self.user,
                "-g",
                self.group,
                "-m",
                "0750",
                "--",
                str(self.rsync.partial_dir),
            ],
            root=True,
        )

        self._ensure_manifest_fingerprint(target)

        result = target.runner.run(
            create_rsync_backup_command(
                manifest=self.rsync.manifest_path,
                source=self.rsync.source_dir,
                destination=self.rsync.partial_dir,
                previous=self.rsync.previous_dir,
            ),
            root=True,
            check=False,
        )

        if result.returncode not in (0, 24):
            raise TargetCommandError(result)

        if result.returncode == 24:
            target.output.warning(
                "Some source files vanished during the backup; "
                "continuing with the completed snapshot."
            )

        target.runner.run(
            [
                "mv",
                "--",
                str(self.rsync.partial_dir),
                str(self.rsync.destination_dir),
            ],
            root=True,
        )

        target.runner.run(
            ["rm", "--", str(self.rsync.manifest_sha256_path)],
            root=True,
        )

    def _ensure_manifest_fingerprint(
            self,
            target: TargetContext,
    ) -> None:
        current_sha256 = BackupRsyncData.fingerprint_manifest(
            self.rsync.manifest_path
        )

        if current_sha256 != self.rsync.manifest_sha256:
            raise BackupSnapshotError(
                "Cannot continue backup snapshot because the backup manifest "
                "changed after the snapshot attempt was initialized."
            )

        metadata = self.rsync.manifest_sha256_path

        if not target.filesystem.exists(metadata, root=True):
            target.filesystem.write_text(
                metadata,
                f"{current_sha256}\n",
                root=True,
            )
            return

        stored_sha256 = target.filesystem.read_text(
            metadata,
            root=True,
        ).strip()

        if stored_sha256 != current_sha256:
            raise BackupSnapshotError(
                "Cannot resume backup snapshot because the backup manifest "
                "changed since the interrupted run."
            )
