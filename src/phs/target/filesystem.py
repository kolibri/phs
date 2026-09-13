from pathlib import Path
from typing import Protocol, final, override

from phs.target.runner import Runner


class Filesystem(Protocol):
    def ensure_mode(self, path: Path, mode: int, *, root: bool = False) -> None: ...

    @property
    def description(self) -> str: ...

    def exists(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> bool: ...

    def read_text(
        self,
        path: Path,
        *,
        root: bool = False,
    ) -> str: ...

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        root: bool = False,
    ) -> None: ...


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
    def ensure_mode(self, path: Path, mode: int, *, root: bool = False) -> None:
        if not 0 <= mode <= 0o7777:
            raise ValueError("File mode must be between 0000 and 7777")
        result = self.runner.run(
            ["stat", "-c", "%a", "--", str(path)], root=root, capture_output=True
        )
        if result.stdout is None:
            raise RuntimeError("Expected captured file mode")
        if int(result.stdout.strip(), 8) != mode:
            self.runner.run(["chmod", f"{mode:04o}", "--", str(path)], root=root)

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
