from typing import Annotated

from cyclopts import Parameter

from phs.config_repository import ConfigRepository
from phs.context import AppContext


def configsync(
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    ConfigRepository(
        context.settings.config_dir,
        context.output,
    ).sync()
