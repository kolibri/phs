from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext


def print_config(
    *,
    host: str | None = None,
    context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    target_host = context.settings.my_hostname if host is None else host
    data = context.inventory.load(target_host)
    context.output.info(f"Showing configuration for {data.hostname}")
    context.output.info(data.to_yaml())
