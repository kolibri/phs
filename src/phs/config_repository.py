import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import final

from phs.output import Output


class ConfigRepositoryError(Exception):
    pass


@final
class ConfigRepository:
    def __init__(
            self,
            path: Path,
            output: Output,
    ) -> None:
        self.path = path
        self.output = output

    def _run(
            self,
            args: Sequence[str],
            *,
            check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            text=True,
            capture_output=True,
            check=False,
        )

        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ConfigRepositoryError(detail or f"Git command failed: git {' '.join(args)}")

        return result

    def require_clean(self) -> None:
        result = self._run(["status", "--porcelain", "--untracked-files=normal"])

        if result.stdout:
            raise ConfigRepositoryError("Configuration repository has uncommitted changes.")

    def commit(self, paths: Sequence[Path], message: str) -> None:
        relative_paths = [
            str(path.relative_to(self.path))
            for path in paths
        ]

        self._run(["add", "--", *relative_paths])
        self._run(["commit", "--message", message])

    def sync(self) -> None:
        self.require_clean()
        self.output.info("Fetching configuration repository.")
        self._run(["fetch"])

        upstream_result = self._run(
            [
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ],
            check=False,
        )

        if upstream_result.returncode != 0:
            raise ConfigRepositoryError("Current configuration branch has no upstream branch.")

        upstream = upstream_result.stdout.strip()
        counts_result = self._run([
            "rev-list",
            "--left-right",
            "--count",
            f"HEAD...{upstream}",
        ])

        parts = counts_result.stdout.split()
        if len(parts) != 2:
            raise ConfigRepositoryError("Could not determine configuration repository sync state.")

        ahead, behind = (int(part) for part in parts)

        if ahead == 0 and behind == 0:
            self.output.success("Configuration repository is synchronized.")
            return

        if ahead > 0 and behind > 0:
            raise ConfigRepositoryError("Configuration repository has diverged from its upstream branch.")

        if behind > 0:
            self.output.info(f"Configuration repository is {behind} commit(s) behind; fast-forwarding.")
            self._run(["merge", "--ff-only", upstream])
            self.output.success("Configuration repository synchronized.")
            return

        self.output.info(f"Configuration repository is {ahead} commit(s) ahead; pushing.")
        self._run(["push"])
        self.output.success("Configuration repository synchronized.")
