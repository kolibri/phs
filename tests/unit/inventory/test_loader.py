from pathlib import Path
from unittest.mock import call, patch

import pytest
import yaml
from pydantic import ValidationError

from phs.inventory.host import HostData
from phs.inventory.loader import HostDataLoader, InventoryError


@pytest.mark.parametrize("source", ["all", "workstation"])
def test_unknown_keys_report_source_without_input_values(defaults, host, source):
    documents = {
        Path("/inventory/all.yaml"): defaults,
        Path("/inventory/workstation.yaml"): host,
    }
    documents[Path(f"/inventory/{source}.yaml")]["unknown"] = "private-value"
    with (
        patch(
            "phs.inventory.loader.load_yaml",
            autospec=True,
            side_effect=documents.__getitem__,
        ) as load,
        pytest.raises(InventoryError) as error,
    ):
        HostDataLoader(Path("/inventory")).load("workstation")
    assert (
        str(error.value)
        == f"Invalid configuration: /inventory/{source}.yaml\n  Unknown key: unknown"
    )
    assert isinstance(error.value.__cause__, ValidationError)
    expected = [call(Path("/inventory/all.yaml"))]
    if source != "all":
        expected.append(call(Path("/inventory/workstation.yaml")))
    assert load.call_args_list == expected


@pytest.mark.parametrize(
    "values,message",
    [
        (
            {"files": [{"target": "/srv/file", "src": "file", "typo": True}]},
            "Unknown key: files.0.typo",
        ),
        ({"files": [{"target": "/srv/file"}]}, "files.0.src: Field required"),
        ({"desktop": {"type": "qtile"}}, "desktop.qtile.config_file: Field required"),
        (
            {"desktop": {"type": "gnome", "extra": True}},
            "Unknown key: desktop.gnome.extra",
        ),
        ({"printers": [{"name": "office"}]}, "printers.0.uri: Field required"),
    ],
)
def test_nested_validation_errors_keep_readable_locations(load_host, values, message):
    with pytest.raises(InventoryError) as error:
        load_host(host_values=values)
    assert (
        str(error.value)
        == f"Invalid configuration: /inventory/workstation.yaml\n  {message}"
    )
    assert isinstance(error.value.__cause__, ValidationError)


def test_all_validation_errors_are_reported(load_host):
    with pytest.raises(InventoryError) as error:
        load_host(host_values={"files": [{"target": "/srv/file"}], "unknown": True})
    assert str(error.value).splitlines() == [
        "Invalid configuration: /inventory/workstation.yaml",
        "  files.0.src: Field required",
        "  Unknown key: unknown",
    ]


def test_loader_reads_yaml_and_returns_serializable_resolved_host(
    tmp_path, defaults, host
):
    (tmp_path / "all.yaml").write_text(
        yaml.safe_dump(
            defaults
            | {
                "packages": ["git"],
                "printers": [{"name": "office", "uri": "ipp://global"}],
            }
        )
    )
    (tmp_path / "workstation.yaml").write_text(
        yaml.safe_dump(
            host
            | {
                "packages": ["vim"],
                "printers": [{"name": "office", "uri": "ipp://host"}],
            }
        )
    )
    data = HostDataLoader(tmp_path).load("workstation")
    assert isinstance(data, HostData)
    assert data.username == defaults["username"]
    assert data.packages == ["git", "vim"]
    assert data.printers[0].uri == "ipp://host"
    assert HostData.model_validate(yaml.safe_load(data.to_yaml())) == data
