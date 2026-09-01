from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionFactory, ExecutionOptions
from phs.executor import Executor
from phs.tasks.copy import Copy
from phs.tasks.pacman import Pacman
from phs.tasks.task import Task


def init(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
):
    execution = ExecutionFactory.create(
        context,
        host=options.host,
        dry_run=options.dry_run,
    )

    data = execution.data

    tasks: list[Task] = [
        Pacman.update(),
        Copy.path(
            Path.cwd(),
            Path(data.homedir) / "projects" / "phs",
            create_dirs=True,
            exclude=[
                "test/qemu/iso",
                "test/qemu/state",
                ".idea",
                ".venv",
                "__pycache__",
            ],
        ),
        Copy.path(
            Path(context.settings.config_dir),
            Path(data.homedir) / ".phs",
            create_dirs=True,
            exclude=[
                "test/qemu/iso",
                "test/qemu/state",
                ".idea",
                ".venv",
                "__pycache__",
            ],
        ),
        #        Aur.install(data.aur_packages, context.builtin_templates),
    ]

    Executor.execute(
        tasks,
        execution.target,
    )
