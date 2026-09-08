from pathlib import Path

import pytest
import yaml

from phs.inventory.config import (
    BackupConfig,
    FileConfig,
    GnomeDesktopConfig,
    HyprlandDesktopConfig,
    NfsSource,
    PrinterConfig,
    QtileDesktopConfig,
)
from phs.inventory.host import HostData


@pytest.mark.parametrize(
    "desktop,model_type",
    [
        ({"type": "gnome"}, GnomeDesktopConfig),
        ({"type": "qtile", "config_file": "/config/qtile.py"}, QtileDesktopConfig),
        (
            {
                "type": "hyprland",
                "hypr_dir": "/config/hypr",
                "waybar_dir": "/config/waybar",
            },
            HyprlandDesktopConfig,
        ),
    ],
)
def test_desktop_variants_validate_and_serialize(load_host, desktop, model_type):
    data = load_host(host_values={"desktop": desktop})
    assert isinstance(data.desktop, model_type)
    assert data.model_dump(mode="json")["desktop"] == desktop
    assert yaml.safe_load(data.to_yaml())["desktop"] == desktop


def test_nested_models_and_paths_round_trip_as_plain_yaml(load_host, defaults, host):
    config = {
        "modules": ["packages", "desktop"],
        "packages": ["git"],
        "aur_packages": ["custom"],
        "files": [{"target": "/etc/example", "src": "files/example", "root": True}],
        "nfs_sources": [
            {"source": "server:/share", "target": "/mnt/share", "options": "ro"}
        ],
        "services": ["example.service"],
        "fonts": ["example-font"],
        "file_associations": {"txt": "editor"},
        "desktop": {"type": "qtile", "config_file": "/config/qtile.py"},
        "backup": {
            "manifest_path": "/backup/manifest",
            "include": ["documents", "file with spaces"],
            "excludes": ["*.tmp"],
            "target_dir": "/backup/snapshots",
        },
        "printers": [{"name": "office", "uri": "ipp://printer", "default": True}],
    }
    data = load_host(host_values=config)
    assert isinstance(data, HostData)
    assert isinstance(data.files[0], FileConfig)
    assert isinstance(data.nfs_sources[0], NfsSource)
    assert isinstance(data.backup, BackupConfig)
    assert isinstance(data.printers[0], PrinterConfig)
    assert data.files[0].target == Path("/etc/example")
    assert data.files[0].src == Path("files/example")
    assert data.nfs_sources[0].target == Path("/mnt/share")
    assert data.desktop.config_file == Path("/config/qtile.py")
    assert data.backup.include == [Path("documents"), Path("file with spaces")]
    assert data.backup.manifest_path == Path("/backup/manifest")
    assert data.backup.target_dir == Path("/backup/snapshots")
    expected = defaults | host | config
    assert data.model_dump(mode="json") == expected
    assert yaml.safe_load(data.to_yaml()) == expected
    assert HostData.model_validate(yaml.safe_load(data.to_yaml())) == data


@pytest.mark.parametrize("optional", [{}, {"desktop": None, "backup": None}])
def test_optional_configs_remain_null(load_host, optional):
    data = load_host(host_values=optional)
    assert data.desktop is None
    assert data.backup is None
    document = yaml.safe_load(data.to_yaml())
    assert document["desktop"] is None
    assert document["backup"] is None


def test_nested_defaults_are_serialized(load_host):
    data = load_host(
        host_values={
            "files": [{"target": "/srv/file", "src": "file"}],
            "printers": [{"name": "office", "uri": "ipp://printer"}],
            "backup": {
                "manifest_path": "/backup/manifest",
                "include": ["docs"],
                "target_dir": "/backup",
            },
        }
    )
    document = data.model_dump(mode="json")
    assert document["files"] == [{"target": "/srv/file", "src": "file", "root": False}]
    assert document["printers"] == [
        {"name": "office", "uri": "ipp://printer", "default": False}
    ]
    assert document["backup"] == {
        "manifest_path": "/backup/manifest",
        "include": ["docs"],
        "target_dir": "/backup",
        "excludes": [],
    }
