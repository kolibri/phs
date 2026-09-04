from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BackupRsync:
    manifest: Path
    source: Path
    destination: Path
    previous: Path | None = None

    def command(
            self,
            *,
            dry_run: bool = False,
            itemize_changes: bool = False,
    ) -> list[str]:
        command = [
            "env",
            "LC_ALL=C",
            "rsync",
            "-aHAX",
            "--numeric-ids",
            "--from0",
            f"--files-from={self.manifest}",
            "--stats",
        ]

        if dry_run:
            command.append("--dry-run")

        if itemize_changes:
            command.append("--itemize-changes")

        if self.previous is not None:
            command.append(
                f"--link-dest={self.previous}"
            )

        command.extend([
            f"{self.source}/",
            f"{self.destination}/",
        ])

        return command
