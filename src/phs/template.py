from pathlib import Path
from typing import Self

from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined


class TemplateRenderer:
    environment: Environment

    def __init__(self, environment: Environment) -> None:
        self.environment = environment

    @classmethod
    def builtin(cls) -> Self:
        return cls(
            Environment(
                loader=PackageLoader("phs", "templates"),
                autoescape=False,
                undefined=StrictUndefined,
            )
        )

    @classmethod
    def from_directory(cls, path: Path) -> Self:
        return cls(
            Environment(
                loader=FileSystemLoader(path),
                autoescape=False,
                undefined=StrictUndefined,
            )
        )

    def render(self, template_name: str, **context: object) -> str:
        template = self.environment.get_template(template_name)
        return template.render(**context)
