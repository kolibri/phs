from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import die, log, require_command
from .vm import VM


@dataclass(frozen=True, slots=True)
class SourceStager:
    project_root: Path
    destination: str
    sut: VM

    def tracked_working_tree_files(self) -> list[Path]:
        require_command("git")
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.project_root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            capture_output=True,
        )
        return [
            Path(os.fsdecode(value)) for value in result.stdout.split(b"\0") if value
        ]

    def create_worktree_tar(self, destination: Path) -> None:
        with tarfile.open(destination, mode="w") as archive:
            for relative in self.tracked_working_tree_files():
                source = self.project_root / relative
                if source.exists() or source.is_symlink():
                    archive.add(
                        source,
                        arcname=os.fspath(relative),
                        recursive=False,
                    )

    def stage(self) -> None:
        log("staging current local PHS source into SUT")
        result = self.sut.run(
            ["test", "-d", f"{self.destination}/.git"],
            check=False,
        )
        if result.returncode != 0:
            die(f"{self.destination}/.git is missing; run the real `phs init` first")

        remote_stage = f"{self.destination}.phs-test-stage"
        self.sut.run(["rm", "-rf", remote_stage])
        self.sut.run(["mkdir", "-p", remote_stage])

        with tempfile.NamedTemporaryFile(
            prefix="phs-working-tree-",
            suffix=".tar",
        ) as temporary:
            self.create_worktree_tar(Path(temporary.name))
            temporary.seek(0)
            self.sut.run(
                ["tar", "-xf", "-", "-C", remote_stage],
                stdin=temporary,
            )

        self.sut.run(
            [
                "find",
                self.destination,
                "-mindepth",
                "1",
                "-maxdepth",
                "1",
                "!",
                "-name",
                ".git",
                "-exec",
                "rm",
                "-rf",
                "--",
                "{}",
                "+",
            ]
        )
        self.sut.run(["cp", "-a", f"{remote_stage}/.", f"{self.destination}/"])
        self.sut.run(["rm", "-rf", remote_stage])
        print(f"Local source staged at {self.destination}")
