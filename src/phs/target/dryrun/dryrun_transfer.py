from pathlib import Path
from typing import final, override, Sequence

from phs.target.transfer import Transfer


@final
class DryRunTransfer(Transfer):
    transferer: Transfer

    def __init__(self, transferer: Transfer) -> None:
        self.transferer = transferer

    @property
    @override
    def description(self) -> str:
        return self.transferer.description

    @override
    def transfer(
        self,
        source: Path,
        destination: Path,
        *,
        root: bool = False,
        create_dirs: bool = False,
        exclude: Sequence[str] = (),
    ) -> None:
        prefix = "sudo " if root else ""

        print(
            f"[dry-run] [{self.transferer.description}] "
            f"{prefix}transfer {source} to {destination}"
        )

        if create_dirs:
            print("[dry-run] create destination directories")

        for pattern in exclude:
            print(f"[dry-run] exclude {pattern}")
