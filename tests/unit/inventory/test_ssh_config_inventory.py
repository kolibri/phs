from unittest.mock import patch

import pytest
import yaml

from phs.inventory.config import SshHostConfig
from phs.inventory.loader import HostDataLoader


def test_yaml_entries_load_and_serialize(defaults, host):
    values = yaml.safe_load("""
ssh_config:
  cid.ko:
    hostname: cid.ko
    port: 2222
  nas:
    hostname: bugenhagen.ko
    user: ko
""")
    with patch(
        "phs.inventory.loader.load_yaml",
        autospec=True,
        side_effect=[defaults, host | values],
    ):
        from pathlib import Path

        data = HostDataLoader(Path("/inventory")).load("workstation")
    assert data.ssh_config["cid.ko"] == SshHostConfig(
        hostname="cid.ko",
        port=2222,
    )
    assert data.ssh_config["nas"].user == "ko"


@pytest.mark.parametrize("values", [{}, {"ssh_config": {}}])
def test_empty_or_omitted_config(load_host, values):
    assert load_host(host_values=values).ssh_config == {}


def test_defaults_merge_by_alias_and_replace_whole_entry(load_host):
    data = load_host(
        {
            "ssh_config": {
                "cid.ko": {"hostname": "cid.ko", "port": 2222},
                "nas": {"user": "ko"},
            }
        },
        {"ssh_config": {"cid.ko": {"user": "other"}, "new": {"port": 22}}},
    )
    assert list(data.ssh_config) == ["cid.ko", "nas", "new"]
    assert data.ssh_config["cid.ko"] == SshHostConfig(user="other")
    assert data.ssh_config["nas"].user == "ko"
    assert data.ssh_config["new"].port == 22


def test_empty_mapping_keeps_global_hosts(load_host):
    assert (
        "cid.ko"
        in load_host(
            {"ssh_config": {"cid.ko": {"port": 2222}}}, {"ssh_config": {}}
        ).ssh_config
    )
