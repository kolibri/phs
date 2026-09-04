from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BackupSnapshotCreate:
    manifest: Path
    source: Path
    destination: Path
    previous: Path | None = None

    def execute(self, target: TargetContext) -> None:
        target.output.info(
            f"Backing up {self.source} to {self.destination}"
        )

        target.runner.run([
            "mkdir",
            "-p",
            str(self.destination),
        ])

        command = [
            "rsync",
            "-aHAX",
            "--numeric-ids",
            "--from0",
            f"--files-from={self.manifest}",
            "--itemize-changes",
            "--stats",
        ]

        if self.previous is not None:
            command.append(f"--link-dest={self.previous}")

        command.extend([
            f"{self.source}/",
            f"{self.destination}/",
        ])

        target.runner.run(command)
