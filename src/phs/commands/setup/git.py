from typing import Annotated

from cyclopts import Parameter

from phs.commands.setup import setup_app
from phs.context import AppContext
from phs.modules.git import git as git_module


@setup_app.command(name="git")
def git(
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    git_module(context)
