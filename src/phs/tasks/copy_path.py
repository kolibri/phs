from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class CopyPath:
    source: Path
    destination: Path
    root: bool = False
    create_dirs: bool = False
    exclude: tuple[str, ...] = ()

    def execute(self, target: TargetContext) -> None:
        target.output.info(
            f"Copy directory {self.source} to {self.destination}"
        )
        target.transfer.transfer(
            self.source,
            self.destination,
            root=self.root,
            create_dirs=self.create_dirs,
            exclude=self.exclude,
        )
