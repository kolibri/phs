from pathlib import Path
from unittest.mock import call

import pytest

from phs.tasks.mount_ensure import MountEnsure


@pytest.mark.parametrize("returncode", [0, 1, 32])
def test_mounts_only_when_mountpoint_check_fails(target, result, returncode):
    target.runner.run.return_value = result(returncode)
    MountEnsure(Path("/mnt/data")).execute(target)
    expected = [call(["mountpoint", "--quiet", "/mnt/data"], check=False)]
    if returncode:
        expected.append(call(["mount", "/mnt/data"], root=True))
    assert target.runner.run.call_args_list == expected
