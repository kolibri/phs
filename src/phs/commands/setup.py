from typing import Annotated

from cyclopts import App, Parameter

from phs.commands.setup_commands.git import git
from phs.commands.setup_commands.nfs import nfs
from phs.commands.setup_commands.packages import packages
from phs.commands.setup_commands.zsh import zsh
from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.git import Git
from phs.modules.nfs import Nfs
from phs.modules.packages import Packages
from phs.modules.zsh import Zsh

setup_app = App(name="setup")
setup_app.command(packages, name="packages")
setup_app.command(git, name="git")
setup_app.command(zsh, name="zsh")
setup_app.command(nfs, name="nfs")

@setup_app.default
def setup(
    *,
    options: ExecutionOptions = ExecutionOptions(),
    context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    run_modules(
        [
            Packages(),
            Git(),
            Zsh(),
            Nfs(),
        ],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
