from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.nfs import Nfs


def nfs(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    run_modules(
        [Nfs()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
