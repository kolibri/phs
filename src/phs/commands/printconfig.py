from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext


def printconfig(
        host: str,
        *,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    data = context.inventory.load(host)
    context.output.info(f"Showing configuration for {data.hostname}")
    context.output.info(data.to_yaml())
