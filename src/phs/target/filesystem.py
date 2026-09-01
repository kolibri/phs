from pathlib import Path
from typing import Protocol, final, override

from phs.target.runner import Runner


class Filesystem(Protocol):
    @property
    def description(self) -> str:
        ...

    def exists(
            self,
            path: Path,
            *,
            root: bool = False,
    ) -> bool:
        ...

    def read_text(
            self,
            path: Path,
            *,
            root: bool = False,
    ) -> str:
        ...

    def write_text(
            self,
            path: Path,
            content: str,
            *,
            root: bool = False,
    ) -> None:
        ...


@final
class RunnerFilesystem(Filesystem):
    runner: Runner

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    @property
    @override
    def description(self) -> str:
        return self.runner.description

    @override
    def exists(
            self,
            path: Path,
            *,
            root: bool = False,
    ) -> bool:
        result = self.runner.run(
            ["test", "-e", str(path)],
            root=root,
            capture_output=True,
            check=False,
        )

        return result.returncode == 0

    @override
    def read_text(
            self,
            path: Path,
            *,
            root: bool = False,
    ) -> str:
        result = self.runner.run(
            ["cat", "--", str(path)],
            root=root,
            capture_output=True,
        )

        if result.stdout is None:
            raise RuntimeError("Expected captured command output")

        return result.stdout

    @override
    def write_text(
            self,
            path: Path,
            content: str,
            *,
            root: bool = False,
    ) -> None:
        self.runner.run(
            ["tee", "--", str(path)],
            root=root,
            input_text=content,
            capture_output=True,
        )
