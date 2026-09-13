from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.setup.ssh_config import SshConfig


def ssh_config(
    *,
    options: ExecutionOptions = ExecutionOptions(),
    context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    context.output.info("Setting up SSH client configuration")
    run_modules(
        [SshConfig()], context=context, host=options.host, dry_run=options.dry_run
    )
