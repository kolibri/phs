from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.setup.desktop import Desktop


def desktop(
    *,
    options: ExecutionOptions = ExecutionOptions(),
    context: Annotated[
        AppContext,
        Parameter(parse=False),
    ],
) -> None:
    context.output.info(f"Setting up desktop")

    run_modules(
        [Desktop()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )