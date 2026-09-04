from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.backup.base import BackupRsync
from phs.backup.size import BackupSizeCalculator
from phs.commands.backup_commands.base import _validate_snapshot_inputs, _latest_snapshot, _new_snapshot_path
from phs.context import AppContext
from phs.execution import ExecutionFactory


def _format_size(value: int) -> str:
    amount = float(value)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if amount < 1024 or unit == "PiB":
            if unit == "B":
                return f"{int(amount)} {unit}"

            return f"{amount:.1f} {unit}"

        amount /= 1024

    raise AssertionError("unreachable")


def backup_size(
        *,

        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
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

    context.output.result(
        f"Total size: {_format_size(size.total)} "
        f"({size.total:,} bytes)"
    )
    context.output.result(
        f"Increment size: {_format_size(size.increment)} "
        f"({size.increment:,} bytes)"
    )
























