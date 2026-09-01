from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class SshkeyEnsure:
    path: Path
    replace: bool
    key_type: str
    comment: str | None

    def execute(self, target: TargetContext) -> None:
        public_path = self.path.with_name(
            f"{self.path.name}.pub"
        )

        private_exists = target.filesystem.exists(self.path)
        public_exists = target.filesystem.exists(public_path)

        if private_exists and public_exists and not self.replace:
            return

        if private_exists != public_exists and not self.replace:
            raise RuntimeError(
                f"Incomplete SSH key pair at {self.path}"
            )

        if self.replace:
            target.runner.run(["rm", "-f", "--", str(self.path), str(public_path)])

        target.runner.run(["mkdir", "-p", "--", str(self.path.parent)])
        target.runner.run(["chmod", "700", str(self.path.parent)])

        command = [
            "ssh-keygen",
            "-t",
            self.key_type,
            "-N",
            "",
            "-f",
            str(self.path),
        ]

        if self.comment is not None:
            command.extend(["-C", self.comment])

        target.runner.run(command)


@final
class Sshkey:
    @staticmethod
    def ensure(
        path: Path,
        *,
        replace: bool = False,
        key_type: str = "ed25519",
        comment: str | None = None,
    ) -> Task:
        return SshkeyEnsure(
            path=path,
            replace=replace,
            key_type=key_type,
            comment=comment,
        )