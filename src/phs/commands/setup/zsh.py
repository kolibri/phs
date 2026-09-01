from typing import Annotated

from cyclopts import Parameter

from phs.commands.setup import setup_app
from phs.context import AppContext
from phs.modules.zsh import zsh as zsh_module


@setup_app.command(name="zsh")
def zsh(
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    zsh_module(context)
