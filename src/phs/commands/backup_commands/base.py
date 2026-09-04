from datetime import datetime, UTC
from pathlib import Path

from phs.context import AppContext


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
