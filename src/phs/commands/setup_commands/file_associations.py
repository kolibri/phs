from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.setup.file_associations import FileAssociations


def file_associations(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Ensuring file associations")

    run_modules(
        [FileAssociations()],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
