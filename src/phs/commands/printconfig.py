from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext


def printconfig(
        host: str,
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    data = context.inventory.load(host)
    print(data.to_yaml())
