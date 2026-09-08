from pathlib import Path
from unittest.mock import patch

import pytest

from phs.inventory.loader import HostDataLoader


@pytest.fixture
def defaults():
    return {
        "username": "default-user",
        "groupname": "default-group",
        "homedir": "/srv/default-user",
        "git_user": "Default User",
        "git_email": "default@example.invalid",
        "shell": "/bin/sh",
    }


@pytest.fixture
def host():
    return {"hostname": "workstation", "ip": "192.0.2.1", "ssh_port": 22, "hdd": ""}


@pytest.fixture
def load_host(defaults, host):
    """Exercise the loader and models, replacing only YAML file I/O."""

    def load(global_values=None, host_values=None):
        documents = {
            Path("/inventory/all.yaml"): defaults | (global_values or {}),
            Path("/inventory/workstation.yaml"): host | (host_values or {}),
        }
        with patch(
            "phs.inventory.loader.load_yaml",
            autospec=True,
            side_effect=documents.__getitem__,
        ):
            return HostDataLoader(Path("/inventory")).load("workstation")

    return load
