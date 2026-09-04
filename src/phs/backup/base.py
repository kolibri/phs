import hashlib
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
        "--ignore-missing-args",
        "--info=progress2,stats1",
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


class BackupSnapshotError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BackupRsyncData:
    _name_format = "%Y-%m-%dT%H%M%S.%fZ"

    manifest_path: Path
    source_dir: Path
    target_dir: Path
    name: str
    previous_dir: Path | None
    manifest_sha256: str

    @property
    def destination_dir(self) -> Path:
        return self.target_dir / self.name

    @property
    def partial_dir(self) -> Path:
        return self.target_dir / f".{self.name}.partial"

    @property
    def manifest_sha256_path(self) -> Path:
        return self.target_dir / (
            f".{self.name}.partial.manifest-sha256"
        )

    @classmethod
    def create(
            cls,
            *,
            manifest: Path,
            source: Path,
            target: Path,
    ) -> "BackupRsyncData":
        partials = cls._partial_snapshots(target)

        if partials:
            names = "\n".join(
                f"  {path.name}"
                for _, path in partials
            )
            label = (
                "Incomplete backup snapshot exists:"
                if len(partials) == 1
                else "Incomplete backup snapshots exist:"
            )

            raise BackupSnapshotError(
                f"{label}\n{names}\n\n"
                "Use:\n"
                "  phs backup snapshot --resume"
            )

        return cls(
            manifest_path=manifest,
            source_dir=source,
            target_dir=target,
            name=datetime.now(UTC).strftime(cls._name_format),
            previous_dir=cls._latest_snapshot(target),
            manifest_sha256=cls.fingerprint_manifest(manifest),
        )

    @classmethod
    def resume(
            cls,
            *,
            manifest: Path,
            source: Path,
            target: Path,
    ) -> "BackupRsyncData":
        partials = cls._partial_snapshots(target)

        if not partials:
            raise BackupSnapshotError(
                "No incomplete backup snapshot found."
            )

        if len(partials) > 1:
            names = "\n".join(
                f"  {path.name}"
                for _, path in partials
            )

            raise BackupSnapshotError(
                "Multiple incomplete backup snapshots found.\n"
                f"{names}\n"
                "Refusing to choose one automatically."
            )

        _, partial = partials[0]
        name = cls._partial_snapshot_name(partial.name)

        if name is None:
            raise AssertionError("validated partial snapshot has no name")

        if (target / name).exists():
            raise BackupSnapshotError(
                "Cannot resume backup snapshot because a completed snapshot "
                "with the same timestamp already exists."
            )

        manifest_sha256 = cls.fingerprint_manifest(manifest)
        metadata = target / (
            f".{name}.partial.manifest-sha256"
        )

        if not metadata.is_file():
            raise BackupSnapshotError(
                "Cannot resume backup snapshot because its manifest "
                "fingerprint metadata is missing."
            )

        try:
            stored_sha256 = metadata.read_text(
                encoding="ascii"
            ).strip()
        except UnicodeDecodeError:
            stored_sha256 = ""

        if stored_sha256 != manifest_sha256:
            raise BackupSnapshotError(
                "Cannot resume backup snapshot because the backup manifest "
                "changed since the interrupted run."
            )

        return cls(
            manifest_path=manifest,
            source_dir=source,
            target_dir=target,
            name=name,
            previous_dir=cls._latest_snapshot(target),
            manifest_sha256=manifest_sha256,
        )

    @staticmethod
    def fingerprint_manifest(manifest: Path) -> str:
        digest = hashlib.sha256()

        with manifest.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)

        return digest.hexdigest()

    @classmethod
    def _partial_snapshots(
            cls,
            target: Path,
    ) -> list[tuple[datetime, Path]]:
        snapshots: list[tuple[datetime, Path]] = []

        for path in target.iterdir():
            if path.is_symlink() or not path.is_dir():
                continue

            name = cls._partial_snapshot_name(path.name)

            if name is None:
                continue

            timestamp = cls._snapshot_timestamp(name)

            if timestamp is None:
                raise AssertionError("validated snapshot has no timestamp")

            snapshots.append((timestamp, path))

        return sorted(snapshots, key=lambda item: item[0])

    @classmethod
    def _partial_snapshot_name(cls, name: str) -> str | None:
        prefix = "."
        suffix = ".partial"

        if not name.startswith(prefix) or not name.endswith(suffix):
            return None

        snapshot_name = name[len(prefix):-len(suffix)]

        if cls._snapshot_timestamp(snapshot_name) is None:
            return None

        return snapshot_name

    @classmethod
    def _snapshot_timestamp(cls, name: str) -> datetime | None:
        try:
            timestamp = datetime.strptime(name, cls._name_format)
        except ValueError:
            return None

        if timestamp.strftime(cls._name_format) != name:
            return None

        return timestamp

    @classmethod
    def _latest_snapshot(cls, target: Path) -> Path | None:
        snapshots: list[tuple[datetime, Path]] = []

        for path in target.iterdir():
            if not path.is_dir():
                continue

            timestamp = cls._snapshot_timestamp(path.name)

            if timestamp is None:
                continue

            snapshots.append((timestamp, path))

        if not snapshots:
            return None

        return max(snapshots, key=lambda item: item[0])[1]
