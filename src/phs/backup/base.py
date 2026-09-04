from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

def create_rsync_backup_command(
        manifest: Path,
        source: Path,
        destination: Path,
        previous: Path | None = None,
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
        "--ignore - missing - args",
        f"--files-from={manifest}",
        "--stats",
    ]

    if dry_run:
        command.append("--dry-run")

    if itemize_changes:
        command.append("--itemize-changes")

    if previous is not None:
        command.append(
            f"--link-dest={previous}"
        )

    command.extend([
        f"{source}/",
        f"{destination}/",
    ])

    return command



@dataclass(frozen=True, slots=True)
class BackupRsyncData:
    _name_format = "%Y-%m-%dT%H%M%S.%fZ"

    manifest_path: Path
    source_dir: Path
    target_dir: Path
    name: str
    previous_dir: Path | None

    @property
    def destination_dir(self) -> Path:
        return self.target_dir / self.name

    @property
    def partial_dir(self) -> Path:
        return self.target_dir / f".{self.name}.partial"

    @classmethod
    def create(
            cls,
            *,
            manifest: Path,
            source: Path,
            target: Path,
    ) -> "BackupRsyncData":
        return cls(
            manifest_path=manifest,
            source_dir=source,
            target_dir=target,
            name=datetime.now(UTC).strftime(cls._name_format),
            previous_dir=cls._latest_snapshot(target),
        )

    @classmethod
    def _latest_snapshot(cls,target: Path) -> Path | None:
        snapshots: list[tuple[datetime, Path]] = []

        for path in target.iterdir():
            if not path.is_dir():
                continue

            try:
                timestamp = datetime.strptime(path.name, cls._name_format)
            except ValueError:
                continue

            snapshots.append((timestamp, path))

        if not snapshots:
            return None

        return max(snapshots, key=lambda item: item[0])[1]
