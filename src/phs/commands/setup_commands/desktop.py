from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.desktop import Desktop


def desktop(
    *,
    options: ExecutionOptions = ExecutionOptions(),
    context: Annotated[
        AppContext,
        Parameter(parse=False),
    ],
) -> None:
    run_modules(
        [
            Desktop(),
        ],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )