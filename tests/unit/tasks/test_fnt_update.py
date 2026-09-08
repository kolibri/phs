from unittest.mock import call

import pytest

from phs.tasks.fnt_update import FntUpdate


@pytest.mark.parametrize("returncode", [0, 1, 127])
def test_updates_only_when_available(target, result, returncode):
    target.runner.run.return_value = result(returncode)
    FntUpdate().execute(target)
    expected = [
        call(
            ["sh", "-c", "command -v fnt >/dev/null 2>&1"],
            capture_output=True,
            check=False,
        )
    ]
    if returncode == 0:
        expected.append(call(["fnt", "update"]))
    assert target.runner.run.call_args_list == expected
