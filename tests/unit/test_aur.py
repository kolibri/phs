import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from phs.tasks.aur_install import (
    AurError,
    AurPackage,
    is_vcs_package,
    parse_rpc_response,
    parse_srcinfo_version,
    query_aur,
)


def rpc_result(**fields):
    return {
        "resultcount": 1,
        "results": [{"PackageBase": "example-base", "Version": "2:1.0-3", **fields}],
    }


def test_rpc_metadata():
    assert parse_rpc_response("example", rpc_result()) == AurPackage(
        "example-base", "2:1.0-3"
    )


def test_package_not_found():
    with pytest.raises(AurError, match="AUR package not found: example"):
        parse_rpc_response("example", {"resultcount": 0, "results": []})


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        "invalid",
        {},
        {"resultcount": True, "results": [{}]},
        {"resultcount": "1", "results": [{}]},
        {"resultcount": 1, "results": []},
        {"resultcount": 0, "results": [{}]},
        {"resultcount": 1},
        {"resultcount": 1, "results": {}},
        {"resultcount": 2, "results": [{}, {}]},
        {"resultcount": 1, "results": [None]},
        {"type": "error", "error": "RPC unavailable"},
    ],
)
def test_malformed_rpc_response(response):
    with pytest.raises(AurError, match="Invalid AUR response for package: example"):
        parse_rpc_response("example", response)


@pytest.mark.parametrize("field", ["PackageBase", "Version"])
@pytest.mark.parametrize("value", [None, "", 123])
def test_invalid_metadata_fields(field, value):
    with pytest.raises(AurError, match=field):
        parse_rpc_response("example", rpc_result(**{field: value}))


@pytest.mark.parametrize("field", ["PackageBase", "Version"])
def test_missing_metadata_fields(field):
    response = rpc_result()
    del response["results"][0][field]
    with pytest.raises(AurError, match=field):
        parse_rpc_response("example", response)


@pytest.mark.parametrize(
    "base", ["../escape", "/absolute", ".", "..", "a/b", "-option", "a b"]
)
def test_package_base_cannot_escape_checkout(base):
    with pytest.raises(AurError, match="PackageBase"):
        parse_rpc_response("example", rpc_result(PackageBase=base))


def test_queries_encoded_rpc_v5_endpoint_and_closes_response():
    response = io.BytesIO(json.dumps(rpc_result()).encode())
    with patch(
        "phs.tasks.aur_install.urlopen", autospec=True, return_value=response
    ) as open_url:
        assert query_aur("example+name&other") == AurPackage("example-base", "2:1.0-3")
    open_url.assert_called_once_with(
        "https://aur.archlinux.org/rpc/v5/info?arg%5B%5D=example%2Bname%26other",
        timeout=30,
    )
    assert response.closed


@pytest.mark.parametrize("body", [b"{invalid", b"\xff", b""])
def test_invalid_json_has_package_context_and_closes_response(body):
    response = io.BytesIO(body)
    with (
        patch("phs.tasks.aur_install.urlopen", autospec=True, return_value=response),
        pytest.raises(
            AurError, match="AUR metadata lookup failed for example"
        ) as error,
    ):
        query_aur("example")
    assert error.value.__cause__ is not None
    assert response.closed


@pytest.mark.parametrize(
    "failure",
    [
        URLError("offline"),
        HTTPError("https://aur.archlinux.org", 503, "unavailable", {}, None),
        TimeoutError("timeout"),
    ],
)
def test_http_failures_have_package_context(failure):
    with (
        patch("phs.tasks.aur_install.urlopen", autospec=True, side_effect=failure),
        pytest.raises(
            AurError, match="AUR metadata lookup failed for example"
        ) as error,
    ):
        query_aur("example")
    assert error.value.__cause__ is failure


@pytest.mark.parametrize(
    "suffix", ["-bzr", "-cvs", "-darcs", "-fossil", "-git", "-hg", "-svn"]
)
def test_vcs_suffixes(suffix):
    assert is_vcs_package(f"example{suffix}")
    assert not is_vcs_package(f"example{suffix}-extra")


@pytest.mark.parametrize(
    "name", ["example", "git", "example-GIT", "example-git ", "", "libgit2"]
)
def test_normal_names(name):
    assert not is_vcs_package(name)


@pytest.mark.parametrize(
    "srcinfo,expected",
    [
        (
            "pkgbase = foo-git\npkgver = 1.2.r10.gabcdef\npkgrel = 1\n",
            "1.2.r10.gabcdef-1",
        ),
        ("epoch = 2\npkgver = 1.2.r10.gabcdef\npkgrel = 3\n", "2:1.2.r10.gabcdef-3"),
        ("\tpkgver = 1.2\r\n    pkgrel = 4\r\n\tepoch = 0\n", "0:1.2-4"),
        (
            "# pkgver = ignored\nsource = git+https://example.invalid?a=b\npkgver = 2\npkgrel = 1\npkgname = split\npkgver = ignored\npkgrel = 99\n",
            "2-1",
        ),
        ("pkgver=2\npkgrel = 1\nepoch = \n", "2-1"),
        ("epoch = 1\nepoch = 2\npkgver = 3\npkgrel = 4", "1:3-4"),
    ],
)
def test_srcinfo_version(srcinfo, expected):
    assert parse_srcinfo_version(srcinfo, package="foo-git") == expected


@pytest.mark.parametrize(
    "srcinfo,missing",
    [
        ("", "pkgver"),
        ("pkgrel = 1", "pkgver"),
        ("pkgver = 2", "pkgrel"),
        ("pkgver = \npkgrel = 1", "pkgver"),
        ("pkgver = 2\npkgrel = ", "pkgrel"),
        ("pkgver 2\npkgrel = 1", "pkgver"),
        ("pkgver = \npkgver = 2\npkgrel = 1", "pkgver"),
    ],
)
def test_srcinfo_missing_values(srcinfo, missing):
    with pytest.raises(AurError, match=f"foo-git: missing {missing}"):
        parse_srcinfo_version(srcinfo, package="foo-git")
