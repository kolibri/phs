from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.docker import Docker


def docker(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    run_modules(
        [Docker()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
