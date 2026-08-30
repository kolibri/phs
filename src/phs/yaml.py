from collections.abc import Mapping
from pathlib import Path
from typing import cast, override

import yaml

type YamlScalar = str | int | float | bool | None
type YamlValue = (
        YamlScalar
        | list[YamlValue]
        | dict[str, YamlValue]
)
type YamlDocument = dict[str, YamlValue]


class IndentedDumper(yaml.SafeDumper):
    @override
    def increase_indent(
            self,
            flow: bool = False,
            indentless: bool = False,
    ) -> None:
        super().increase_indent(flow, False)


def load_yaml(path: Path) -> YamlDocument:
    with path.open() as file:
        data = cast(YamlValue, yaml.safe_load(file))

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise TypeError(f"Expected YAML mapping in {path}")

    return data


def dump_yaml(data: Mapping[str, object]) -> str:
    return yaml.dump(
        data,
        Dumper=IndentedDumper,
        sort_keys=False,
        default_flow_style=False,
    )
