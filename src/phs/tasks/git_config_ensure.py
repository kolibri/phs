from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class GitConfigEnsure:
    values: tuple[tuple[str, str], ...]

    def execute(self, target: TargetContext) -> None:
        for key, value in self.values:
            result = target.runner.run(
                [
                    "git",
                    "config",
                    "--global",
                    "--get",
                    key,
                ],
                capture_output=True,
                check=False,
            )

            current = (
                result.stdout.strip()
                if result.returncode == 0 and result.stdout is not None
                else None
            )

            if current == value:
                continue

            target.output.info(f"Ensuring git config {key}")
            target.runner.run([
                "git",
                "config",
                "--global",
                key,
                value,
            ])
