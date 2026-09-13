from pathlib import Path

import pytest

from phs.inventory.config import SshHostConfig
from phs.ssh_config import INCLUDE, ensure_ssh_include, render_ssh_config


def test_full_soft_serve_example():
    assert render_ssh_config(
        {
            "cid.ko": SshHostConfig(
                hostname="cid.ko",
                port=2222,
            )
        }
    ) == (
        "# Managed by phs. Do not edit manually.\n\n"
        "Host cid.ko\n"
        "    HostName cid.ko\n"
        "    Port 2222\n"
    )


@pytest.mark.parametrize(
    "values,line",
    [
        ({"hostname": "bugenhagen.ko"}, "    HostName bugenhagen.ko\n"),
        ({"user": "ko"}, "    User ko\n"),
        ({"port": 2222}, "    Port 2222\n"),
        ({}, ""),
        (
            {
                "hostname": None,
                "port": None,
                "user": None,
            },
            "",
        ),
    ],
)
def test_optional_directives(values, line):
    assert (
        render_ssh_config({"nas": SshHostConfig(**values)})
        == "# Managed by phs. Do not edit manually.\n\nHost nas\n" + line
    )


def test_multiple_hosts_keep_inventory_precedence_and_stable_spacing():
    hosts = {
        "nas": SshHostConfig(hostname="bugenhagen.ko", user="ko"),
        "*.ko !excluded.ko": SshHostConfig(port=2222),
        "*": SshHostConfig(hostname="hojo.ko"),
    }
    expected = (
        "# Managed by phs. Do not edit manually.\n\n"
        "Host nas\n    HostName bugenhagen.ko\n    User ko\n\n"
        "Host *.ko !excluded.ko\n    Port 2222\n\n"
        "Host *\n    HostName hojo.ko\n"
    )
    assert render_ssh_config(hosts) == expected
    assert render_ssh_config(hosts) == expected
    assert expected.count("Host ") == 3


def test_empty_configuration():
    assert render_ssh_config({}) == "# Managed by phs. Do not edit manually.\n"


@pytest.mark.parametrize(
    "before",
    [
        "",
        "Host github.com\n    IdentityFile ~/.ssh/github\n",
        "# personal ssh config\n\nHost foo\n    HostName foo.example",
        "# Include ~/.ssh/config.d/*\nHost foo\n",
        "  # Include config.d/*\n",
    ],
)
def test_inserts_include_without_changing_existing_content(before):
    result = ensure_ssh_include(before, Path("/remote/ko"))
    assert result == INCLUDE + "\n" + ("\n" + before if before else "")
    assert ensure_ssh_include(result, Path("/remote/ko")) == result


@pytest.mark.parametrize(
    "line",
    [
        "Include ~/.ssh/config.d/*",
        'include "~/.ssh/config.d/*"',
        "  INCLUDE=config.d/* # personal comment",
        "Include /remote/ko/.ssh/config.d/*",
        "Include other.conf config.d/*",
        "Include = config.d/*",
    ],
)
def test_equivalent_global_include_is_preserved(line):
    before = "# keep this header\n\n" + line + "\nHost foo\n    User ko\n"
    assert ensure_ssh_include(before, Path("/remote/ko")) == before


@pytest.mark.parametrize("section", ["Host foo", "Match host foo", "Host=foo"])
def test_relocates_conditional_standalone_include_preserving_other_lines(section):
    before = f"# personal\n{section}\n    User ko\n    Include config.d/* # phs\n    Port 23\n"
    expected = f"    Include config.d/* # phs\n\n# personal\n{section}\n    User ko\n    Port 23\n"
    assert ensure_ssh_include(before, Path("/remote/ko")) == expected
    assert ensure_ssh_include(expected, Path("/remote/ko")) == expected


def test_crlf_and_no_final_newline_are_preserved():
    before = "# personal\r\nHost foo\r\n    User ko"
    assert (
        ensure_ssh_include(before, Path("/remote/ko")) == INCLUDE + "\r\n\r\n" + before
    )


def test_unrelated_include_is_preserved():
    before = "Include ~/.ssh/work/*\nHost foo\n"
    assert ensure_ssh_include(before, Path("/remote/ko")) == INCLUDE + "\n\n" + before


@pytest.mark.parametrize(
    "before", ['Include "unterminated\n', "Host foo\nInclude config.d/* work.conf\n"]
)
def test_ambiguous_includes_fail_instead_of_changing_user_scope(before):
    with pytest.raises(ValueError, match="Include"):
        ensure_ssh_include(before, Path("/remote/ko"))
