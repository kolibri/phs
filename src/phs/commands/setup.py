from typing import Annotated

from cyclopts import App, Parameter

from phs.context import AppContext
from phs.modules.git import git as git_module
from phs.modules.zsh import zsh as zsh_module

setup_app = App(name="setup")


@setup_app.default
def setup(
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    git_module(context)
    zsh_module(context)
