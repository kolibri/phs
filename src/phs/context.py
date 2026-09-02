from dataclasses import dataclass

from phs.inventory import HostDataLoader
from phs.output import Output
from phs.settings import Settings
from phs.ssh import SSHRunner
from phs.template import TemplateRenderer


@dataclass(frozen=True, slots=True)
class AppContext:
    output: Output
    settings: Settings
    inventory: HostDataLoader
    builtin_templates: TemplateRenderer
    config_templates: TemplateRenderer
    ssh: SSHRunner
