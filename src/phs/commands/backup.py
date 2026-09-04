from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from phs.backup import BackupManifestGenerator
from phs.context import AppContext
from phs.execution import ExecutionOptions, ExecutionFactory
from phs.executor import Executor
from phs.tasks.backup_manifest_write import BackupManifestWrite

backup = App(name="backup")


def backup_manifest(
        *,
        show: bool = False,
        dry_run: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Creating backup manifest")

    data = context.inventory.load(context.settings.my_hostname)

    if data.backup is None:
        context.output.error("No backup configured. Aborting")
        return

    execution = ExecutionFactory.create(
        context,
        host='local',
        dry_run=dry_run,
    )
    manifest = BackupManifestGenerator.generate(
        source=Path(data.homedir),
        includes=data.backup.include,
        excludes=data.backup.excludes,
    )

    if show:
        context.output.text(manifest.as_text())
        return

    Executor.execute(
        [BackupManifestWrite(manifest=manifest, path=Path(data.backup.manifest_path))],
        execution.target,
    )


backup.command(backup_manifest, name="manifest")
