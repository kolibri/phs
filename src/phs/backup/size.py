import re
from dataclasses import dataclass
from pathlib import Path

from phs.backup.base import backup_rsync_command, BackupRsync
from phs.target.context import TargetContext


@dataclass(frozen=True, slots=True)
class BackupSize:
    total: int
    increment: int


class BackupSizeCalculator:
    @staticmethod
    def calculate(
            target: TargetContext,
            rsync: BackupRsync
    ) -> BackupSize:
        result = target.runner.run(
            rsync.command(dry_run=True),
            root=True,
            capture_output=True,
        )

        if result.stdout is None:
            raise RuntimeError("rsync did not return size statistics")

        return BackupSize(
            total=BackupSizeCalculator._parse_stat(
                result.stdout,
                "Total file size",
            ),
            increment=BackupSizeCalculator._parse_stat(
                result.stdout,
                "Total transferred file size",
            ),
        )

    @staticmethod
    def _parse_stat(
            output: str,
            name: str,
    ) -> int:
        print(output)
        match = re.search(
            rf"^{re.escape(name)}:\s+([\d,]+)\s+bytes$",
            output,
            re.MULTILINE,
        )

        if match is None:
            raise RuntimeError(
                f"Could not find rsync statistic: {name}"
            )

        return int(match.group(1).replace(",", ""))
