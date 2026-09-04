from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import App, Parameter
from rich.console import Console

from phs.commands.backup import backup
from phs.commands.add import add
from phs.commands.authorize import authorize
from phs.commands.configsync import configsync
from phs.commands.init import init
from phs.commands.install import install
from phs.commands.printconfig import printconfig
from phs.commands.setup import setup_app
from phs.commands.watch import watch
from phs.config_repository import ConfigRepositoryError
from phs.context import AppContext
from phs.inventory import HostDataLoader
from phs.output import RichOutput
from phs.settings import Settings
from phs.ssh import SSHRunner
from phs.target.base import TargetCommandError
from phs.template import TemplateRenderer

console = Console()
CONFIG_FILE = Path.home() / ".phs.yaml"

app = App(
    console=console,
    config=cyclopts.config.Yaml(
        CONFIG_FILE,
        must_exist=False,
        use_commands_as_keys=False,
    )
)

app.command(configsync)
app.command(install)
app.command(printconfig)
app.command(init)
app.command(authorize)
app.command(setup_app)
app.command(watch)
app.command(add)
app.command(backup)


@app.meta.default
def main(
        *tokens: Annotated[
            str,
            Parameter(show=False, allow_leading_hyphen=True),
        ],
        settings: Settings = Settings()
):
    settings = Settings(
        config_dir=settings.config_dir.expanduser(),
        sshkey=settings.sshkey.expanduser(),
    )

    context = AppContext(
        output=RichOutput(console),
        settings=settings,
        inventory=HostDataLoader(settings.config_dir),
        builtin_templates=TemplateRenderer.builtin(),
        config_templates=TemplateRenderer.from_directory(settings.config_dir / "files"),
        ssh=SSHRunner(),
    )

    command, bound, ignored = app.parse_args(tokens)

    additional_kwargs: dict[str, object] = {}

    if "context" in ignored:
        additional_kwargs["context"] = context

    try:
        return command(
            *bound.args,
            **bound.kwargs,
            **additional_kwargs,
        )
    except ConfigRepositoryError as error:
        context.output.error(str(error))
        raise SystemExit(1) from None
    except TargetCommandError as error:
        result = error.result
        context.output.error(f"Command failed with exit code {result.returncode}")
        context.output.result(" ".join(result.command))

        if result.stdout:
            context.output.text(result.stdout.rstrip())

        if result.stderr:
            context.output.error(result.stderr.rstrip())

        raise SystemExit(result.returncode or 1) from None


def run():
    app.meta()
