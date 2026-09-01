from pathlib import Path
from typing import final, override, Sequence

from phs.target.runner import Runner
from phs.target.transfer import Transfer


@final
class LocalTransfer(Transfer):
    runner: Runner

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    @property
    @override
    def description(self) -> str:
        return self.runner.description

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
        if not source.exists():
            raise FileNotFoundError(source)

        if create_dirs:
            directory = (
                destination
                if source.is_dir()
                else destination.parent
            )

            self.runner.run(
                ["mkdir", "-p", "--", str(directory)],
                root=root,
            )

        exclude_args: list[str] = []

        for pattern in exclude:
            exclude_args.extend([
                "--exclude",
                pattern,
            ])

        source_arg = (
            f"{source}/"
            if source.is_dir()
            else str(source)
        )

        self.runner.run(
            [
                "rsync",
                "-a",
                *exclude_args,
                "--",
                source_arg,
                str(destination),
            ],
            root=root,
        )
