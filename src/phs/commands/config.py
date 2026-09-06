from cyclopts import App

from phs.commands.config_commands.print import print_config
from phs.commands.config_commands.sync import sync_config

config = App(name="config")

config.command(print_config, name="print")
config.command(sync_config, name="sync")
