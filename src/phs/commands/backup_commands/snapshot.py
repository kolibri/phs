from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.backup.base import BackupRsyncData, BackupSnapshotError
from phs.commands.backup_commands.base import _validate_snapshot_inputs
from phs.context import AppContext
from phs.execution import ExecutionFactory
from phs.executor import Executor
from phs.tasks.backup_snapshot_create import BackupSnapshotCreate


def backup_snapshot(
        *,
        dry_run: bool = False,
        resume: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Creating backup snapshot")

    data = context.inventory.load(context.settings.my_hostname)

    if data.backup is None:
        context.output.error("No backup configured. Aborting")
        return

    manifest_path = Path(data.backup.manifest_path)
    target_dir = Path(data.backup.target_dir)

    if not _validate_snapshot_inputs(
            manifest=manifest_path,
            target_dir=target_dir,
            context=context,
    ):
        return

    try:
        factory = (
            BackupRsyncData.resume
            if resume
            else BackupRsyncData.create
        )
        rsync_data = factory(
            manifest=manifest_path,
            source=Path(data.homedir),
            target=target_dir,
        )

        execution = ExecutionFactory.create(
            context,
            host="local",
            dry_run=dry_run,
        )

        Executor.execute(
            [BackupSnapshotCreate(rsync=rsync_data, user=data.username, group=data.groupname)],
            execution.target,
        )
    except BackupSnapshotError as error:
        context.output.error(str(error))
        return

    if not dry_run:
        context.output.success(
            f"Created backup snapshot {rsync_data.destination_dir}"
        )
