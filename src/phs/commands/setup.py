from typing import Annotated

from cyclopts import App, Parameter

from phs.commands.setup_commands.desktop import desktop
from phs.commands.setup_commands.docker import docker
from phs.commands.setup_commands.font import font
from phs.commands.setup_commands.git import git
from phs.commands.setup_commands.nfs import nfs
from phs.commands.setup_commands.packages import packages
from phs.commands.setup_commands.services import services
from phs.commands.setup_commands.zsh import zsh
from phs.context import AppContext
from phs.execution import ExecutionFactory, ExecutionOptions
from phs.modules.base import Module, execute_modules
from phs.modules.setup.desktop import Desktop
from phs.modules.setup.docker import Docker
from phs.modules.setup.font import Font
from phs.modules.setup.git import Git
from phs.modules.setup.nfs import Nfs
from phs.modules.setup.packages import Packages
from phs.modules.setup.services import Services
from phs.modules.setup.zsh import Zsh

setup_app = App(name="setup")
setup_app.command(packages, name="packages")
setup_app.command(git, name="git")
setup_app.command(zsh, name="zsh")
setup_app.command(nfs, name="nfs")
setup_app.command(desktop, name="desktop")
setup_app.command(docker, name="docker")
setup_app.command(font, name="font")
setup_app.command(services, name="services")

MODULES: dict[str, Module] = {
    "packages": Packages(),
    "git": Git(),
    "zsh": Zsh(),
    "nfs": Nfs(),
    "desktop": Desktop(),
    "docker": Docker(),
    "font": Font(),
    "services": Services(),
}


def _parse_ignored_modules(value: str) -> set[str]:
    return {
        module.strip()
        for module in value.split(",")
        if module.strip()
    }


def _select_modules(
        configured: list[str],
        ignored: set[str],
) -> list[Module]:
    unknown = set(configured).difference(MODULES)
    if unknown:
        raise ValueError(
            f"Unknown configured module(s): {', '.join(sorted(unknown))}"
        )

    unknown_ignored = ignored.difference(MODULES)
    if unknown_ignored:
        raise ValueError(
            f"Unknown ignored module(s): {', '.join(sorted(unknown_ignored))}"
        )

    return [
        MODULES[name]
        for name in configured
        if name not in ignored
    ]


@setup_app.default
def setup(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        ignore_modules: str = "",
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution = ExecutionFactory.create(
        context,
        host=options.host,
        dry_run=options.dry_run,
    )

    modules = _select_modules(
        execution.data.modules,
        _parse_ignored_modules(ignore_modules),
    )

    context.output.info(f"Starting setup host {execution.data.hostname}.")
    context.output.info(f"Configured modules: {' '.join(type(module).__name__.lower() for module in modules)}.")

    execute_modules(
        modules,
        context=context,
        execution=execution,
    )

    context.output.success(f"Finished setup host {execution.data.hostname}.")
