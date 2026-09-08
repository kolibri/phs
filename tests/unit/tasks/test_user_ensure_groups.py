from unittest.mock import call

import pytest

from phs.tasks.user_ensure_groups import UserEnsureGroups


@pytest.mark.parametrize(
    "groups,stdout,missing",
    [
        ((), None, ()),
        (("wheel",), "wheel audio\n", ()),
        (("wheel", "docker"), " audio\twheel\n", ("docker",)),
        (("wheel", "docker"), None, ("wheel", "docker")),
        (("wheel",), "wheelchair", ("wheel",)),
    ],
)
def test_appends_only_missing_groups_in_requested_order(
    target, result, groups, stdout, missing
):
    target.runner.run.return_value = result(stdout=stdout)
    UserEnsureGroups("alice", groups).execute(target)
    expected = [call(["id", "--name", "--groups", "alice"], capture_output=True)]
    if missing:
        expected.append(
            call(
                ["usermod", "--append", "--groups", ",".join(missing), "alice"],
                root=True,
            )
        )
    assert target.runner.run.call_args_list == expected
