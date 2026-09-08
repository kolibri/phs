from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.setup.printer import Printer


def printer(
    *,
    options: ExecutionOptions = ExecutionOptions(),
    context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Setting up printer")

    run_modules(
        [Printer()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
