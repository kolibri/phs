from cyclopts import App

from phs.commands.backup_commands.manifest import backup_manifest
from phs.commands.backup_commands.snapshot import backup_snapshot
from phs.commands.backup_commands.size import backup_size

backup = App(name="backup")



backup.command(backup_manifest, name="manifest")
backup.command(backup_snapshot, name="snapshot")
backup.command(backup_size, name="size")
