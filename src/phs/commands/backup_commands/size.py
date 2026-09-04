from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators

from phs.backup.base import BackupRsync
from phs.backup.size import BackupSizeCalculator, BackupSizeRenderer
from phs.commands.backup_commands.base import _validate_snapshot_inputs, _latest_snapshot, _new_snapshot_path
from phs.context import AppContext
from phs.execution import ExecutionFactory


def backup_size(
        *,
        depth: Annotated[
            int,
            Parameter(validator=validators.Number(gte=0)),
        ] = 1,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    if depth < 0:
        raise ValueError("depth must be greater than or equal to 0")

    context.output.info("Calculating backup size")

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

    previous = _latest_snapshot(target_dir)

    execution = ExecutionFactory.create(
        context,
        host="local",
        dry_run=False,
    )

    rsync = BackupRsync(
        manifest=manifest,
        source=Path(data.homedir),
        destination=_new_snapshot_path(target_dir),
        previous=previous,
    )

    size = BackupSizeCalculator.calculate(execution.target, rsync)

    context.output.text(
        BackupSizeRenderer.render(size, depth=depth)
    )
