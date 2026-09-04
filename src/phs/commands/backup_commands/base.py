from datetime import datetime, UTC
from pathlib import Path

from phs.context import AppContext


def _new_snapshot_path(target_dir: Path) -> Path:
    return target_dir / datetime.now(UTC).strftime(
        _SNAPSHOT_NAME_FORMAT
    )


def _latest_snapshot(target_dir: Path) -> Path | None:
    snapshots: list[tuple[datetime, Path]] = []

    for path in target_dir.iterdir():
        if not path.is_dir():
            continue

        try:
            timestamp = datetime.strptime(
                path.name,
                _SNAPSHOT_NAME_FORMAT,
            )
        except ValueError:
            continue

        snapshots.append((timestamp, path))

    if not snapshots:
        return None

    return max(
        snapshots,
        key=lambda item: item[0],
    )[1]


def _validate_snapshot_inputs(
        *,
        manifest: Path,
        target_dir: Path,
        context: AppContext,
) -> bool:
    if not manifest.is_file():
        context.output.error(
            f"Backup manifest does not exist: {manifest}. "
            "Run 'phs backup manifest' first."
        )
        return False

    if not target_dir.is_dir():
        context.output.error(
            f"Backup target directory does not exist: {target_dir}"
        )
        return False

    return True


_SNAPSHOT_NAME_FORMAT = "%Y-%m-%dT%H%M%S.%fZ"
