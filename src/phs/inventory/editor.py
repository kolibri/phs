from collections.abc import MutableMapping, MutableSequence
from dataclasses import dataclass
from difflib import unified_diff
from io import StringIO
from pathlib import Path
from typing import cast, final

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from phs.output import Output


@final
@dataclass(frozen=True, slots=True)
class InventoryChange:
    path: Path
    before: str
    after: str

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def show(self, output: Output) -> None:
        if not self.changed:
            output.info(f"Configuration already contains the requested value: {self.path}")
            return

        output.info(f"Would update configuration {self.path}")

        diff = "".join(unified_diff(
            self.before.splitlines(keepends=True),
            self.after.splitlines(keepends=True),
            fromfile=f"current:{self.path}",
            tofile=f"desired:{self.path}",
        ))

        if diff:
            output.text(diff.rstrip())

    def apply(self) -> None:
        if self.changed:
            self.path.write_text(self.after)


@final
class InventoryEditor:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.indent(
            mapping=2,
            sequence=4,
            offset=2,
        )

    def add_package(self, hostname: str, package: str) -> InventoryChange:
        return self._add_list_value(hostname, "packages", package)

    def add_aur_package(self, hostname: str, package: str) -> InventoryChange:
        return self._add_list_value(hostname, "aur_packages", package)

    def add_font(self, hostname: str, font: str, ) -> InventoryChange:
        return self._add_list_value(hostname, "fonts", font)

    def add_service(self, hostname: str, service: str, ) -> InventoryChange:
        return self._add_list_value(hostname, "services", service)

    def set_file_association(self, hostname: str, extension: str, application: str, ) -> InventoryChange:
        path, before, data = self._load(hostname)
        associations = self._string_mapping(data, "file_associations", path, )
        extension = extension.removeprefix(".")

        if associations.get(extension) == application:
            return InventoryChange(path, before, before, )
        associations[extension] = application

        return InventoryChange(path, before, self._dump(data), )

    def _add_list_value(self, hostname: str, key: str, value: str) -> InventoryChange:
        path, before, data = self._load(hostname)
        values = self._string_list(data, key, path)

        if value in values:
            return InventoryChange(path, before, before)
        values.append(value)

        return InventoryChange(path, before, self._dump(data))

    def _load(self, hostname: str) -> tuple[Path, str, MutableMapping[str, object]]:
        path = self.config_dir / f"{hostname}.yaml"
        before = path.read_text()
        loaded = cast(object, self._yaml.load(before))

        if not isinstance(loaded, MutableMapping):
            raise TypeError(f"Expected YAML mapping in {path}")

        return path, before, loaded

    def _dump(self, data: MutableMapping[str, object]) -> str:
        output = StringIO()
        self._yaml.dump(data, output)
        return output.getvalue()

    @staticmethod
    def _string_list(data: MutableMapping[str, object], key: str, path: Path) -> MutableSequence[str]:
        value = data.get(key)

        if value is None:
            values = CommentedSeq()
            data[key] = values
            return cast(MutableSequence[str], values)

        if (
                not isinstance(value, MutableSequence)
                or isinstance(value, str)
                or not all(isinstance(item, str) for item in value
        )
        ):
            raise TypeError(f"Expected {key} to be a list of strings in {path}")

        return value

    @staticmethod
    def _string_mapping(data: MutableMapping[str, object], key: str, path: Path) -> MutableMapping[str, str]:
        value = data.get(key)

        if value is None:
            mapping = CommentedMap()
            data[key] = mapping
            return cast(MutableMapping[str, str], mapping)

        if (
                not isinstance(value, MutableMapping)
                or not all(
            isinstance(mapping_key, str)
            and isinstance(mapping_value, str)
            for mapping_key, mapping_value in value.items()
        )
        ):
            raise TypeError(f"Expected {key} to be a string mapping in {path}")

        return value
