from collections.abc import Sequence
from typing import Protocol

from phs.context import AppContext
from phs.execution import Execution, ExecutionFactory
from phs.executor import Executor
from phs.inventory import HostData
from phs.tasks.task import Task


def execute_modules(
        modules: Sequence[Module],
        *,
        context: AppContext,
        execution: Execution,
) -> None:
    tasks: list[Task] = []

    for module in modules:
        tasks.extend(
            module.tasks(
                context,
                execution.data,
            )
        )

    Executor.execute(
        tasks,
        execution.target,
    )


def run_modules(
        modules: Sequence[Module],
        *,
        context: AppContext,
        host: str,
        dry_run: bool,
) -> None:
    execution = ExecutionFactory.create(
        context,
        host=host,
        dry_run=dry_run,
    )

    execute_modules(
        modules,
        context=context,
        execution=execution,
    )


class Module(Protocol):
    def tasks(
            self,
            context: AppContext,
            data: HostData,
    ) -> Sequence[Task]:
        ...
