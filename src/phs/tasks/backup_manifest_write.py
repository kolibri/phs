from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.backup import BackupManifest
from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class BackupManifestWrite:
    manifest: BackupManifest
    path: Path

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Writing backup manifest to {self.path}")

        target.runner.run(["mkdir","-p",str(self.path.parent)])

        target.filesystem.write_text(
            self.path,
            self.manifest.as_rsync(),
        )
