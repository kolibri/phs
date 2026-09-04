from dataclasses import dataclass
from pathlib import Path


def backup_rsync_command(
        *,
        manifest: Path,
        source: Path,
        destination: Path,
        previous: Path | None = None,
        dry_run: bool = False,
) -> list[str]:
    command = [
        "env",
        "LC_ALL=C",
        "rsync",
        "-aHAX",
        "--numeric-ids",
        "--from0",
        f"--files-from={manifest}",
        "--itemize-changes",
        "--stats",
    ]

    if dry_run:
        command.append("--dry-run")

    if previous is not None:
        command.append(f"--link-dest={previous}")

    command.extend([
        f"{source}/",
        f"{destination}/",
    ])

    return command


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

        if self.previous is not None:
            command.append(
                f"--link-dest={self.previous}"
            )

        command.extend([
            f"{self.source}/",
            f"{self.destination}/",
        ])

        return command
