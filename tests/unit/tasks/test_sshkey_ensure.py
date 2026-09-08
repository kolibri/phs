from pathlib import Path
from unittest.mock import call

import pytest

from phs.tasks.sshkey_ensure import SshkeyEnsure


@pytest.mark.parametrize(
    "private,public", [(False, False), (False, True), (True, False), (True, True)]
)
@pytest.mark.parametrize("replace", [False, True])
def test_key_pair_states(target, private, public, replace):
    target.filesystem.exists.side_effect = [private, public]
    task = SshkeyEnsure(Path("/srv/keys/id"), replace=replace)
    if private != public and not replace:
        with pytest.raises(RuntimeError, match="Incomplete SSH key pair"):
            task.execute(target)
        target.runner.run.assert_not_called()
    else:
        task.execute(target)
        expected = []
        if replace:
            expected.append(
                call(["rm", "-f", "--", "/srv/keys/id", "/srv/keys/id.pub"])
            )
        if replace or not private:
            expected.extend(
                [
                    call(["mkdir", "-p", "--", "/srv/keys"]),
                    call(["chmod", "700", "/srv/keys"]),
                    call(
                        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", "/srv/keys/id"]
                    ),
                ]
            )
        assert target.runner.run.call_args_list == expected
    assert target.filesystem.exists.call_args_list == [
        call(Path("/srv/keys/id")),
        call(Path("/srv/keys/id.pub")),
    ]


@pytest.mark.parametrize("comment", ["alice@example.invalid", ""])
def test_custom_key_type_and_comment(target, comment):
    target.filesystem.exists.return_value = False
    SshkeyEnsure(Path("/srv/keys/id"), key_type="rsa", comment=comment).execute(target)
    assert target.runner.run.call_args_list == [
        call(["mkdir", "-p", "--", "/srv/keys"]),
        call(["chmod", "700", "/srv/keys"]),
        call(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", "/srv/keys/id", "-C", comment]
        ),
    ]
