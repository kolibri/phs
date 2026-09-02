from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.setup.font import Font


def font(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info(f"Ensuring fonts")

    run_modules(
        [Font()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
