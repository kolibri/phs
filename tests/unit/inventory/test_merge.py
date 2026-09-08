from copy import deepcopy
from pathlib import Path

import pytest

from phs.inventory.host import AllHostDataFragment, HostData, HostDataFragment
from phs.inventory.merge import merge_host_data


@pytest.mark.parametrize(
    "field", ["username", "groupname", "homedir", "git_user", "git_email", "shell"]
)
@pytest.mark.parametrize(
    "override", [{}, {"value": None}, {"value": ""}, {"value": "host-value"}]
)
def test_scalar_override_and_legacy_empty_inheritance(
    load_host, defaults, field, override
):
    values = {field: override["value"]} if override else {}
    data = load_host(host_values=values)
    assert getattr(data, field) == (override.get("value") or defaults[field])


@pytest.mark.parametrize(
    "override,expected",
    [
        ({}, ["packages", "git"]),
        ({"modules": None}, ["packages", "git"]),
        ({"modules": []}, []),
        ({"modules": ["desktop", "desktop"]}, ["desktop", "desktop"]),
    ],
)
def test_modules_replace_including_explicit_empty(load_host, override, expected):
    assert load_host({"modules": ["packages", "git"]}, override).modules == expected


@pytest.mark.parametrize("field", ["packages", "aur_packages", "services", "fonts"])
@pytest.mark.parametrize(
    "base,override,expected",
    [
        (["a", "b", "a"], {}, ["a", "b"]),
        (["a", "b", "a"], {"value": []}, ["a", "b"]),
        (["a", "b", "a"], {"value": ["b", "c", "c", "d"]}, ["a", "b", "c", "d"]),
        ([], {"value": ["c", "c", "d"]}, ["c", "d"]),
        ([], {}, []),
    ],
)
def test_unique_lists_preserve_order(load_host, field, base, override, expected):
    host_values = {field: override["value"]} if override else {}
    assert getattr(load_host({field: base}, host_values), field) == expected


@pytest.mark.parametrize(
    "base,override,expected",
    [
        ({"txt": "editor", "pdf": "viewer"}, {}, {"txt": "editor", "pdf": "viewer"}),
        ({"txt": "editor"}, {"file_associations": {}}, {"txt": "editor"}),
        (
            {"txt": "editor", "pdf": "viewer"},
            {"file_associations": {"txt": "other", "png": "images"}},
            {"txt": "other", "pdf": "viewer", "png": "images"},
        ),
        ({}, {"file_associations": {"txt": "editor"}}, {"txt": "editor"}),
    ],
)
def test_mapping_overrides_only_matching_keys(load_host, base, override, expected):
    assert (
        load_host({"file_associations": base}, override).file_associations == expected
    )


@pytest.fixture(params=["files", "nfs_sources", "printers"])
def object_list(request):
    field = request.param

    def entry(identity, value, flag=False):
        if field == "files":
            return {"target": f"/srv/{identity}", "src": value, "root": flag}
        if field == "nfs_sources":
            return {
                "source": f"server:/{identity}",
                "target": f"/mnt/{value}",
                "options": "ro",
            }
        return {"name": identity, "uri": f"ipp://{value}", "default": flag}

    return field, entry


def test_object_lists_replace_whole_entries_at_original_position(
    load_host, object_list
):
    field, entry = object_list
    base = [entry("a", "first"), entry("b", "old", True), entry("a", "last-default")]
    override = [entry("b", "new"), entry("c", "first-host"), entry("c", "last-host")]
    data = load_host({field: base}, {field: override})
    assert data.model_dump(mode="json")[field] == [
        entry("a", "last-default"),
        entry("b", "new"),
        entry("c", "last-host"),
    ]


@pytest.mark.parametrize("explicit_empty", [False, True])
def test_global_only_object_lists_survive_empty_or_missing_host(
    load_host, object_list, explicit_empty
):
    field, entry = object_list
    value = entry("a", "global")
    override = {field: []} if explicit_empty else {}
    assert load_host({field: [value, value]}, override).model_dump(mode="json")[
        field
    ] == [value]


def test_host_only_object_lists_are_deduplicated(load_host, object_list):
    field, entry = object_list
    assert load_host(
        host_values={field: [entry("a", "old"), entry("a", "new")]}
    ).model_dump(mode="json")[field] == [entry("a", "new")]


@pytest.mark.parametrize(
    "field,base,override,expected",
    [
        (
            "files",
            {"target": "/srv/file", "src": "old", "root": True},
            {"target": "/srv/./file", "src": "new"},
            {"target": "/srv/file", "src": "new", "root": False},
        ),
        (
            "printers",
            {"name": "office", "uri": "ipp://old", "default": True},
            {"name": "office", "uri": "ipp://new"},
            {"name": "office", "uri": "ipp://new", "default": False},
        ),
    ],
)
def test_replacement_uses_host_model_defaults_not_default_entry_fields(
    load_host, field, base, override, expected
):
    assert load_host({field: [base]}, {field: [override]}).model_dump(mode="json")[
        field
    ] == [expected]


def test_merge_does_not_mutate_fragments_or_share_mutable_values(defaults, host):
    global_config = AllHostDataFragment.model_validate(
        defaults
        | {"files": [{"target": "/srv/file", "src": "old"}], "packages": ["git"]}
    )
    host_config = HostDataFragment.model_validate(
        host | {"files": [{"target": "/srv/file", "src": "new"}]}
    )
    before = deepcopy((global_config, host_config))
    data = HostData.model_validate(merge_host_data(global_config, host_config))
    data.files[0].src = Path("changed")
    data.packages.append("vim")
    assert (global_config, host_config) == before


def test_independent_instances_do_not_share_collection_defaults(defaults, host):
    first = HostData.model_validate(defaults | host)
    second = HostData.model_validate(defaults | host)
    first.packages.append("git")
    first.file_associations["txt"] = "editor"
    assert second.packages == []
    assert second.file_associations == {}
