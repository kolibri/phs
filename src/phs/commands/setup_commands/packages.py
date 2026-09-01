from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions, ExecutionFactory
from phs.executor import Executor
from phs.tasks.aur import Aur
from phs.tasks.pacman import Pacman
from phs.tasks.task import Task


def packages(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution = ExecutionFactory.create(
        context,
        host=options.host,
        dry_run=options.dry_run,
    )

    data = execution.data

    tasks: list[Task] = [
        Pacman.update(),
        Pacman.install(data.packages),
        Aur.install(data.aur_packages, context.builtin_templates),
    ]

    Executor.execute(
        tasks,
        execution.target,
    )
