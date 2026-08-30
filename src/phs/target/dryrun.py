from collections.abc import Sequence
from pathlib import Path
from typing import final, override

from phs.target.base import CommandResult, Target


@final
class DryRunTarget(Target):
    target: Target

    def __init__(self, target: Target) -> None:
        self.target = target

    @override
    def run(
        self,
        command: Sequence[str],
        *,
        root: bool = False,
        input_text: str | None = None,
        capture_output: bool = False,
        check: bool = True,
    ) -> CommandResult:
        prefix = "sudo " if root else ""
        print(f"[dry-run] {prefix}{' '.join(command)}")

        if input_text is not None:
            print("[dry-run] stdin:")
            print(input_text)

        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout=None,
            stderr=None,
        )

    @override
    def exists(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> bool:
        return self.target.exists(path, root=root)

    @override
    def read_text(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> str:
        return self.target.read_text(path, root=root)

    @override
    def write_text(
        self,
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> None:
        print(f"[dry-run] write {path}")