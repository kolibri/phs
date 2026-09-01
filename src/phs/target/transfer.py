from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class Transfer(Protocol):
    @property
    def description(self) -> str:
        ...

    def transfer(
            self,
            source: Path,
            destination: Path,
            *,
            root: bool = False,
            create_dirs: bool = False,
            exclude: Sequence[str] = (),
    ) -> None:
        ...
