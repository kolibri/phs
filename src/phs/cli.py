from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import App, Parameter

from phs.commands.init import init
from phs.commands.install import install
from phs.commands.printconfig import printconfig
from phs.context import AppContext
from phs.inventory import HostDataLoader
from phs.settings import Settings
from phs.ssh import SSHRunner
from phs.template import TemplateRenderer

CONFIG_FILE = Path.home() / ".phs.yaml"

app = App(
    config=cyclopts.config.Yaml(
        CONFIG_FILE,
        must_exist=False,
        use_commands_as_keys=False,
    )
)

app.command(install)
app.command(printconfig)
app.command(init)


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
        settings=settings,
        inventory=HostDataLoader(settings.config_dir),
        builtin_templates=TemplateRenderer.builtin(),
        config_templates=TemplateRenderer.from_directory(settings.config_dir / "templates"),
        ssh=SSHRunner(),
    )

    command, bound, ignored = app.parse_args(tokens)

    additional_kwargs: dict[str, object] = {}

    if "context" in ignored:
        additional_kwargs["context"] = context

    return command(
        *bound.args,
        **bound.kwargs,
        **additional_kwargs,
    )


def run():
    app.meta()
