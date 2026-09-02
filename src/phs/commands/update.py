from typing import Annotated

from cyclopts import App, Parameter

from phs.commands.update_commands.aur import aur
from phs.commands.update_commands.font import font
from phs.commands.update_commands.pacman import pacman
from phs.context import AppContext
from phs.execution import ExecutionOptions
from phs.modules.base import run_modules
from phs.modules.update.aur import Aur
from phs.modules.update.font import Font
from phs.modules.update.pacman import Pacman

update_app = App(name="update")
update_app.command(pacman, name="pacman")
update_app.command(aur, name="aur")
update_app.command(font, name="font")


@update_app.default
def update(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    run_modules(
        [
            Pacman(),
            Aur(),
            Font(),
        ],
        context=context,
        host=options.host,
        dry_run=options.dry_run,
    )
