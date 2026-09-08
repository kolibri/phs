from pathlib import Path

from pydantic import ValidationError

from phs.inventory.host import AllHostDataFragment, HostData, HostDataFragment
from phs.inventory.merge import merge_host_data
from phs.yaml import load_yaml


class InventoryError(Exception):
    pass


def format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Invalid configuration: {path}"]
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"])
        if item["type"] == "extra_forbidden":
            lines.append(f"  Unknown key: {location}")
        else:
            lines.append(f"  {location}: {item['msg']}")
    return "\n".join(lines)


class HostDataLoader:
    def __init__(self, config_dir: Path):
        self.config_dir: Path = config_dir

    def load(self, hostname: str) -> HostData:
        all_path = self.config_dir / "all.yaml"
        host_path = self.config_dir / f"{hostname}.yaml"
        try:
            all_config = AllHostDataFragment.model_validate(load_yaml(all_path))
        except ValidationError as error:
            raise InventoryError(format_validation_error(all_path, error)) from error

        try:
            host_config = HostDataFragment.model_validate(load_yaml(host_path))
            return HostData.model_validate(merge_host_data(all_config, host_config))
        except ValidationError as error:
            raise InventoryError(format_validation_error(host_path, error)) from error
