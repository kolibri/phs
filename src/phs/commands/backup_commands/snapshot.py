from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.backup.base import BackupRsync
from phs.commands.backup_commands.base import _new_snapshot_path, _latest_snapshot, _validate_snapshot_inputs
from phs.context import AppContext
from phs.execution import ExecutionFactory
from phs.executor import Executor
from phs.tasks.backup_snapshot_create import BackupSnapshotCreate


def backup_snapshot(
        *,
        dry_run: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Creating backup snapshot")

    data = context.inventory.load(context.settings.my_hostname)

    if data.backup is None:
        context.output.error("No backup configured. Aborting")
        return

    manifest = Path(data.backup.manifest_path)
    target_dir = Path(data.backup.target_dir)

    if not _validate_snapshot_inputs(
            manifest=manifest,
            target_dir=target_dir,
            context=context,
    ):
        return

    destination = _new_snapshot_path(target_dir)
    previous = _latest_snapshot(target_dir)

    execution = ExecutionFactory.create(
        context,
        host="local",
        dry_run=dry_run,
    )

    rsync = BackupRsync(
        manifest=manifest,
        source=Path(data.homedir),
        destination=_new_snapshot_path(target_dir),
        previous=previous,
    )

    Executor.execute(
        [
            BackupSnapshotCreate(rsync)
        ],
        execution.target,
    )

    if not dry_run:
        context.output.success(
            f"Created backup snapshot {destination}"
        )





















