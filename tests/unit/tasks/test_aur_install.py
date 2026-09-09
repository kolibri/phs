import io
import json
from pathlib import Path
from unittest.mock import Mock, call, patch
from urllib.error import HTTPError, URLError

import pytest

from phs.target.base import TargetCommandError
from phs.target.dryrun.dryrun_runner import DryRunRunner
from phs.tasks.aur_install import (
    AurError,
    AurInstall,
    AurPackage,
    compare_versions,
    installed_version,
    is_vcs_package,
    parse_rpc_response,
    parse_srcinfo_version,
    query_aur,
    target_cache_root,
)


@pytest.fixture
def rpc():
    with patch(
        "phs.tasks.aur_install.query_aur",
        autospec=True,
        return_value=AurPackage("base", "2-1"),
    ) as lookup:
        yield lookup


@pytest.mark.parametrize(
    "code,stdout,expected",
    [
        (0, "example 1:2-3\n", "1:2-3"),
        (0, "example\t2-1\n", "2-1"),
        (1, None, None),
        (1, "error output", None),
    ],
)
def test_installed_version_probe(target, result, code, stdout, expected):
    target.runner.run.return_value = result(code, stdout)
    assert installed_version(target, "example") == expected
    target.runner.run.assert_called_once_with(
        ["pacman", "-Q", "example"], capture_output=True, check=False
    )


@pytest.mark.parametrize(
    "stdout", [None, "", "example", "other 1-1", "example 1-1\nother 2-1"]
)
def test_malformed_successful_installed_version(target, result, stdout):
    target.runner.run.return_value = result(stdout=stdout)
    with pytest.raises(AurError, match="Invalid pacman -Q output.*example"):
        installed_version(target, "example")


@pytest.mark.parametrize(
    "stdout,expected", [("1\n", 1), ("0", 0), ("-1\n", -1), (" +2 \n", 2)]
)
def test_compares_versions_using_vercmp(target, result, stdout, expected):
    target.runner.run.return_value = result(stdout=stdout)
    assert compare_versions(target, "2-1", "1-1") == expected
    target.runner.run.assert_called_once_with(
        ["vercmp", "2-1", "1-1"], capture_output=True
    )


@pytest.mark.parametrize("stdout", [None, "", "newer", "1.0", "1\n0", "1_0"])
def test_rejects_invalid_comparison(target, result, stdout):
    target.runner.run.return_value = result(stdout=stdout)
    with pytest.raises(AurError, match="Invalid vercmp output"):
        compare_versions(target, "2-1", "1-1")


@pytest.mark.parametrize(
    "environment,expected",
    [
        ("HOME=/remote/user\0", "/remote/user/.cache/phs/aur"),
        ("HOME=/remote/user\0XDG_CACHE_HOME=\0", "/remote/user/.cache/phs/aur"),
        (
            "HOME=/remote/user\0XDG_CACHE_HOME=/remote/cache space\0",
            "/remote/cache space/phs/aur",
        ),
        ("XDG_CACHE_HOME=/cache\0", "/cache/phs/aur"),
        ("OTHER=anything\nHOME=/wrong\0HOME=/real=a\0", "/real=a/.cache/phs/aur"),
    ],
)
def test_cache_uses_only_target_environment(
    target, result, monkeypatch, environment, expected
):
    monkeypatch.setenv("HOME", "/controller/home")
    monkeypatch.setenv("XDG_CACHE_HOME", "/controller/cache")
    target.runner.run.return_value = result(stdout=environment)
    assert target_cache_root(target) == Path(expected)
    target.runner.run.assert_called_once_with(["env", "-0"], capture_output=True)


@pytest.mark.parametrize("environment", [None, "", "HOME=\0", "OTHER=value\0"])
def test_missing_target_home_is_an_error(target, result, environment):
    target.runner.run.return_value = result(stdout=environment)
    with pytest.raises(AurError, match="target HOME is missing"):
        target_cache_root(target)


def normal_calls():
    return [
        call(["mktemp", "-d", "-t", "phs-aur.XXXXXX"], capture_output=True),
        call(
            [
                "git",
                "clone",
                "https://aur.archlinux.org/base.git",
                "/target/tmp/phs-aur.abc/base",
            ]
        ),
        call(
            ["makepkg", "--syncdeps", "--install", "--needed", "--noconfirm"],
            cwd=Path("/target/tmp/phs-aur.abc/base"),
        ),
        call(["rm", "-rf", "--", "/target/tmp/phs-aur.abc"]),
    ]


@pytest.mark.parametrize(
    "installed,comparison", [(None, None), ("1-1", "1"), ("2-1", "0"), ("3-1", "-1")]
)
def test_normal_install_decisions_and_cleanup(
    target, result, rpc, installed, comparison
):
    responses = [
        result(1) if installed is None else result(stdout=f"example {installed}\n")
    ]
    expected = [call(["pacman", "-Q", "example"], capture_output=True, check=False)]
    if installed is not None:
        responses.append(result(stdout=comparison))
        expected.append(call(["vercmp", "2-1", installed], capture_output=True))
    if comparison is None or int(comparison) > 0:
        responses.extend(
            [result(stdout="/target/tmp/phs-aur.abc\n"), result(), result(), result()]
        )
        expected.extend(normal_calls())
    target.runner.run.side_effect = responses
    AurInstall(("example",)).execute(target)
    rpc.assert_called_once_with("example")
    assert target.runner.run.call_args_list == expected


@pytest.mark.parametrize("failure_index", [1, 2])
def test_normal_cleanup_after_clone_or_build_failure(
    target, result, rpc, failure_index
):
    failure = TargetCommandError(result(2))
    responses = [result(1), result(stdout="/target/tmp/phs-aur.abc\n")]
    if failure_index == 2:
        responses.append(result())
    responses += [failure, result()]
    target.runner.run.side_effect = responses
    with pytest.raises(TargetCommandError) as error:
        AurInstall(("example", "later")).execute(target)
    assert error.value is failure
    assert target.runner.run.call_args_list == [
        call(["pacman", "-Q", "example"], capture_output=True, check=False),
        *normal_calls()[: failure_index + 1],
        normal_calls()[-1],
    ]
    rpc.assert_called_once_with("example")


@pytest.mark.parametrize(
    "temporary", [None, "", "/", "relative", "/target/tmp/unexpected"]
)
def test_invalid_temporary_directory_never_triggers_cleanup(
    target, result, rpc, temporary
):
    target.runner.run.side_effect = [result(1), result(stdout=temporary)]
    with pytest.raises(AurError, match="Invalid temporary build directory"):
        AurInstall(("example",)).execute(target)
    assert target.runner.run.call_args_list == [
        call(["pacman", "-Q", "example"], capture_output=True, check=False),
        normal_calls()[0],
    ]


def test_metadata_failure_stops_before_target_commands(target, rpc):
    rpc.side_effect = AurError("AUR package not found: missing")
    with pytest.raises(AurError, match="missing"):
        AurInstall(("missing", "later")).execute(target)
    rpc.assert_called_once_with("missing")
    target.runner.run.assert_not_called()


def test_successful_packages_are_processed_in_order(target, result, rpc):
    operations = Mock()
    operations.attach_mock(rpc, "rpc")
    operations.attach_mock(target.runner.run, "run")
    target.runner.run.side_effect = [
        result(stdout="first 2-1"),
        result(stdout="0"),
        result(stdout="second 2-1"),
        result(stdout="0"),
    ]
    AurInstall(("first", "second")).execute(target)
    assert operations.mock_calls == [
        call.rpc("first"),
        call.run(["pacman", "-Q", "first"], capture_output=True, check=False),
        call.run(["vercmp", "2-1", "2-1"], capture_output=True),
        call.rpc("second"),
        call.run(["pacman", "-Q", "second"], capture_output=True, check=False),
        call.run(["vercmp", "2-1", "2-1"], capture_output=True),
    ]


def test_empty_packages(target, rpc):
    AurInstall(()).execute(target)
    rpc.assert_not_called()
    target.runner.run.assert_not_called()


def test_dry_run_does_not_query_network_or_target(target, rpc):
    from dataclasses import replace

    runner = target.runner
    target = replace(target, runner=DryRunRunner(runner))
    AurInstall(("example", "example-git")).execute(target)
    rpc.assert_not_called()
    runner.run.assert_not_called()
    assert target.output.info.call_args_list == [
        call("Would ensure AUR package example"),
        call("Would ensure AUR package example-git"),
    ]


def vcs_calls(
    package, base, *, existing, installed=None, comparison=None, candidate="3-1"
):
    directory = Path("/remote/cache/phs/aur") / base
    expected = [
        call(["pacman", "-Q", package], capture_output=True, check=False),
        call(["env", "-0"], capture_output=True),
        call(["mkdir", "-p", "--", "/remote/cache/phs/aur"]),
        call(["test", "-d", str(directory / ".git")], capture_output=True, check=False),
    ]
    if existing:
        expected += [
            call(["git", "-C", str(directory), "fetch", "--prune", "origin"]),
            call(["git", "-C", str(directory), "reset", "--hard", "@{upstream}"]),
        ]
    else:
        expected += [
            call(["rm", "-rf", "--", str(directory)]),
            call(
                [
                    "git",
                    "clone",
                    f"https://aur.archlinux.org/{base}.git",
                    str(directory),
                ]
            ),
        ]
    expected += [
        call(
            ["makepkg", "--cleanbuild", "--nobuild", "--syncdeps", "--noconfirm"],
            cwd=directory,
        ),
        call(["makepkg", "--printsrcinfo"], cwd=directory, capture_output=True),
    ]
    if installed is not None:
        expected.append(call(["vercmp", candidate, installed], capture_output=True))
    if comparison is None or comparison > 0:
        expected.append(
            call(
                [
                    "makepkg",
                    "--noextract",
                    "--syncdeps",
                    "--install",
                    "--needed",
                    "--noconfirm",
                ],
                cwd=directory,
            )
        )
    return expected


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "installed,comparison", [(None, None), ("2-1", 1), ("3-1", 0), ("4-1", -1)]
)
@pytest.mark.parametrize("epoch", ["", "epoch = 2\n"])
def test_vcs_refreshes_candidate_before_install_decision(
    target, result, rpc, existing, installed, comparison, epoch
):
    rpc.return_value = AurPackage("base-git", "unrelated-rpc-version")
    responses = [
        result(1) if installed is None else result(stdout=f"example {installed}"),
        result(stdout="XDG_CACHE_HOME=/remote/cache\0"),
        result(),
        result(0 if existing else 1),
        result(),
        result(),
        result(),
        result(stdout=f"{epoch}pkgver = 3\npkgrel = 1\n"),
    ]
    if installed is not None:
        responses.append(result(stdout=str(comparison)))
    if comparison is None or comparison > 0:
        responses.append(result())
    target.runner.run.side_effect = responses
    AurInstall(("example",)).execute(target)
    assert target.runner.run.call_args_list == vcs_calls(
        "example",
        "base-git",
        existing=existing,
        installed=installed,
        comparison=comparison,
        candidate="2:3-1" if epoch else "3-1",
    )


@pytest.mark.parametrize(
    "suffix", ["-bzr", "-cvs", "-darcs", "-fossil", "-git", "-hg", "-svn"]
)
@pytest.mark.parametrize("vcs_source", ["package", "base"])
def test_requested_name_or_base_selects_vcs_workflow(
    target, result, rpc, suffix, vcs_source
):
    package = f"example{suffix}" if vcs_source == "package" else "example"
    base = f"base{suffix}" if vcs_source == "base" else "base"
    rpc.return_value = AurPackage(base, "2-1")
    target.runner.run.side_effect = [
        result(1),
        result(stdout="XDG_CACHE_HOME=/remote/cache\0"),
        result(),
        result(1),
        result(),
        result(),
        result(),
        result(stdout="pkgver = 3\npkgrel = 1"),
        result(),
    ]
    AurInstall((package,)).execute(target)
    assert target.runner.run.call_args_list == vcs_calls(package, base, existing=False)


@pytest.mark.parametrize(
    "srcinfo,missing",
    [(None, "pkgver"), ("pkgrel = 1", "pkgver"), ("pkgver = 3", "pkgrel")],
)
def test_invalid_srcinfo_stops_without_removing_cache(
    target, result, rpc, srcinfo, missing
):
    rpc.return_value = AurPackage("base-git", "2-1")
    target.runner.run.side_effect = [
        result(1),
        result(stdout="XDG_CACHE_HOME=/remote/cache\0"),
        result(),
        result(),
        result(),
        result(),
        result(),
        result(stdout=srcinfo),
    ]
    with pytest.raises(AurError, match=f"example: missing {missing}"):
        AurInstall(("example",)).execute(target)
    assert (
        target.runner.run.call_args_list
        == vcs_calls("example", "base-git", existing=True)[:-1]
    )


@pytest.mark.parametrize("failure_index", [2, 4, 5, 6, 7, 8])
def test_vcs_command_failure_stops_and_preserves_cache(
    target, result, rpc, failure_index
):
    rpc.return_value = AurPackage("base-git", "2-1")
    responses = [
        result(1),
        result(stdout="XDG_CACHE_HOME=/remote/cache\0"),
        result(),
        result(),
        result(),
        result(),
        result(),
        result(stdout="pkgver = 3\npkgrel = 1"),
        result(),
    ]
    failure = TargetCommandError(result(2))
    responses[failure_index] = failure
    target.runner.run.side_effect = responses
    with pytest.raises(TargetCommandError) as error:
        AurInstall(("example", "later")).execute(target)
    assert error.value is failure
    assert (
        target.runner.run.call_args_list
        == vcs_calls("example", "base-git", existing=True)[: failure_index + 1]
    )
    rpc.assert_called_once_with("example")


def test_failed_cache_probe_does_not_remove_checkout(target, result, rpc):
    rpc.return_value = AurPackage("base-git", "2-1")
    failure = result(127)
    target.runner.run.side_effect = [
        result(1),
        result(stdout="XDG_CACHE_HOME=/remote/cache\0"),
        result(),
        failure,
    ]
    with pytest.raises(TargetCommandError) as error:
        AurInstall(("example",)).execute(target)
    assert error.value.result is failure
    assert (
        target.runner.run.call_args_list
        == vcs_calls("example", "base-git", existing=True)[:4]
    )


@pytest.mark.parametrize("stage", ["mktemp", "cleanup"])
def test_normal_temporary_directory_errors_are_not_suppressed(
    target, result, rpc, stage
):
    failure = TargetCommandError(result(1))
    responses = [result(1)]
    expected = [call(["pacman", "-Q", "example"], capture_output=True, check=False)]
    if stage == "mktemp":
        responses.append(failure)
        expected.append(normal_calls()[0])
    else:
        responses.extend(
            [result(stdout="/target/tmp/phs-aur.abc\n"), result(), result(), failure]
        )
        expected.extend(normal_calls())
    target.runner.run.side_effect = responses
    with pytest.raises(TargetCommandError) as error:
        AurInstall(("example", "later")).execute(target)
    assert error.value is failure
    assert target.runner.run.call_args_list == expected
    rpc.assert_called_once_with("example")


def test_cleanup_completes_before_next_package(target, result, rpc):
    operations = Mock()
    operations.attach_mock(rpc, "rpc")
    operations.attach_mock(target.runner.run, "run")
    target.runner.run.side_effect = [
        result(1),
        result(stdout="/target/tmp/phs-aur.abc\n"),
        result(),
        result(),
        result(),
        result(stdout="second 2-1"),
        result(stdout="0"),
    ]
    AurInstall(("first", "second")).execute(target)
    assert operations.mock_calls == [
        call.rpc("first"),
        call.run(["pacman", "-Q", "first"], capture_output=True, check=False),
        call.run(["mktemp", "-d", "-t", "phs-aur.XXXXXX"], capture_output=True),
        call.run(
            [
                "git",
                "clone",
                "https://aur.archlinux.org/base.git",
                "/target/tmp/phs-aur.abc/base",
            ]
        ),
        call.run(
            ["makepkg", "--syncdeps", "--install", "--needed", "--noconfirm"],
            cwd=Path("/target/tmp/phs-aur.abc/base"),
        ),
        call.run(["rm", "-rf", "--", "/target/tmp/phs-aur.abc"]),
        call.rpc("second"),
        call.run(["pacman", "-Q", "second"], capture_output=True, check=False),
        call.run(["vercmp", "2-1", "2-1"], capture_output=True),
    ]


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
