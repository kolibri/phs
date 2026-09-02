from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionFactory


def watch(
        *,
        host: str = "local",
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution = ExecutionFactory.create(
        context,
        host=host,
        dry_run=False,
    )

    context.output.info(f"Checking watched files on {execution.data.hostname}.")

    if not execution.target.watch.show_changes():
        context.output.success("No watched files changed.")
