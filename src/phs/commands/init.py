from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.executor import Executor
from phs.modules.aur import Aur
from phs.modules.pacman import Pacman
from phs.modules.task import Task
from phs.target.base import Target
from phs.target.dryrun import DryRunTarget


def init(
        host: str,
        *,
        dry_run: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    data = context.inventory.load(host)
    print("init system")

    tasks: list[Task] = [
        Pacman.update(),
        Pacman.install(data.packages),
        Aur.install(data.aur_packages, context.builtin_templates),
    ]

    target: Target = context.target

    if dry_run:
        target = DryRunTarget(target)


    Executor.execute(tasks, target)