import pytest
from pydantic import ValidationError

from phs.inventory.config import (
    BackupConfig,
    FileConfig,
    GnomeDesktopConfig,
    HyprlandDesktopConfig,
    NfsSource,
    PrinterConfig,
    QtileDesktopConfig,
)
from phs.inventory.host import AllHostDataFragment, HostData, HostDataFragment


@pytest.mark.parametrize(
    "model,required",
    [
        (
            AllHostDataFragment,
            ["username", "groupname", "homedir", "git_user", "git_email", "shell"],
        ),
        (HostDataFragment, ["hostname", "ip", "ssh_port", "hdd"]),
        (
            HostData,
            [
                "hostname",
                "ip",
                "ssh_port",
                "hdd",
                "username",
                "groupname",
                "homedir",
                "git_user",
                "git_email",
                "shell",
            ],
        ),
    ],
)
def test_required_host_fields_remain_required(defaults, host, model, required):
    values = (
        defaults
        if model is AllHostDataFragment
        else host
        if model is HostDataFragment
        else defaults | host
    )
    for field in required:
        with pytest.raises(ValidationError) as error:
            model.model_validate(
                {key: value for key, value in values.items() if key != field}
            )
        assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
            ((field,), "missing")
        ]


@pytest.mark.parametrize("model", [AllHostDataFragment, HostDataFragment, HostData])
def test_unknown_host_keys_are_rejected(defaults, host, model):
    values = (
        defaults
        if model is AllHostDataFragment
        else host
        if model is HostDataFragment
        else defaults | host
    )
    with pytest.raises(ValidationError) as error:
        model.model_validate(values | {"pakages": []})
    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        (("pakages",), "extra_forbidden")
    ]


@pytest.mark.parametrize(
    "model,values",
    [
        (FileConfig, {"src": "file", "target": "/srv/file"}),
        (
            NfsSource,
            {"source": "server:/share", "target": "/mnt/share", "options": "ro"},
        ),
        (PrinterConfig, {"name": "office", "uri": "ipp://printer"}),
        (
            BackupConfig,
            {
                "manifest_path": "/backup/manifest",
                "include": ["docs"],
                "target_dir": "/backup",
            },
        ),
        (GnomeDesktopConfig, {"type": "gnome"}),
        (QtileDesktopConfig, {"type": "qtile", "config_file": "/config/qtile.py"}),
        (
            HyprlandDesktopConfig,
            {
                "type": "hyprland",
                "hypr_dir": "/config/hypr",
                "waybar_dir": "/config/waybar",
            },
        ),
    ],
)
def test_nested_models_reject_unknown_keys_and_require_their_fields(model, values):
    with pytest.raises(ValidationError) as error:
        model.model_validate(values | {"unknown": True})
    assert error.value.errors()[0]["type"] == "extra_forbidden"
    for field in values:
        with pytest.raises(ValidationError) as error:
            model.model_validate(
                {key: value for key, value in values.items() if key != field}
            )
        assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
            ((field,), "missing")
        ]


@pytest.mark.parametrize(
    "desktop,error_type",
    [
        ({}, "union_tag_not_found"),
        ({"type": "unknown"}, "union_tag_invalid"),
        ({"type": "qtile"}, "missing"),
        ({"type": "hyprland", "hypr_dir": "/config/hypr"}, "missing"),
        ({"type": "gnome", "config_file": "/config/qtile.py"}, "extra_forbidden"),
    ],
)
def test_invalid_desktop_discriminators_and_variant_fields(host, desktop, error_type):
    with pytest.raises(ValidationError) as error:
        HostDataFragment.model_validate(host | {"desktop": desktop})
    assert error.value.errors()[0]["type"] == error_type
    assert error.value.errors()[0]["loc"][0] == "desktop"


@pytest.mark.parametrize(
    "field", ["hostname", "ip", "ssh_port", "hdd", "desktop", "backup"]
)
def test_host_only_fields_remain_disallowed_in_defaults(defaults, host, field):
    with pytest.raises(ValidationError) as error:
        AllHostDataFragment.model_validate(defaults | {field: host.get(field)})
    assert error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    "field",
    [
        "packages",
        "aur_packages",
        "files",
        "nfs_sources",
        "services",
        "fonts",
        "printers",
        "file_associations",
    ],
)
def test_null_collections_are_not_treated_as_omitted(host, field):
    with pytest.raises(ValidationError) as error:
        HostDataFragment.model_validate(host | {field: None})
    assert error.value.errors()[0]["loc"] == (field,)


def test_backup_requires_at_least_one_include(host):
    with pytest.raises(ValidationError) as error:
        HostDataFragment.model_validate(
            host
            | {
                "backup": {
                    "manifest_path": "/backup/manifest",
                    "include": [],
                    "target_dir": "/backup",
                }
            }
        )
    assert error.value.errors()[0]["loc"] == ("backup", "include")
    assert error.value.errors()[0]["type"] == "too_short"


def test_existing_pydantic_coercion_is_preserved(load_host):
    data = load_host(
        host_values={
            "ssh_port": "2222",
            "files": [{"target": "/srv/file", "src": "file", "root": "true"}],
        }
    )
    assert data.ssh_port == 2222
    assert data.files[0].root is True


def test_fragment_tracks_omitted_null_and_explicit_empty_modules(host):
    omitted = HostDataFragment.model_validate(host)
    null = HostDataFragment.model_validate(host | {"modules": None})
    empty = HostDataFragment.model_validate(host | {"modules": []})
    assert "modules" not in omitted.model_fields_set
    assert "modules" in null.model_fields_set
    assert "modules" in empty.model_fields_set
    assert "modules" not in null.model_dump(exclude_unset=True, exclude_none=True)
    assert empty.model_dump(exclude_unset=True, exclude_none=True)["modules"] == []
