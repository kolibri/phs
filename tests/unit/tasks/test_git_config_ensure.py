from unittest.mock import call

import pytest

from phs.tasks.git_config_ensure import GitConfigEnsure


@pytest.mark.parametrize(
    "code,stdout,changed",
    [
        (0, " Alice \n", False),
        (0, "Bob", True),
        (1, "Alice", True),
        (0, None, True),
        (1, None, True),
    ],
)
def test_sets_missing_or_different_values(target, result, code, stdout, changed):
    target.runner.run.return_value = result(code, stdout)
    GitConfigEnsure((("user.name", "Alice"),)).execute(target)
    expected = [
        call(
            ["git", "config", "--global", "--get", "user.name"],
            capture_output=True,
            check=False,
        )
    ]
    if changed:
        expected.append(call(["git", "config", "--global", "user.name", "Alice"]))
    assert target.runner.run.call_args_list == expected


def test_continues_after_already_correct_value(target, result):
    target.runner.run.side_effect = [result(stdout="Alice"), result(1), result()]
    GitConfigEnsure(
        (("user.name", "Alice"), ("user.email", "a@example.invalid"))
    ).execute(target)
    assert target.runner.run.call_args_list == [
        call(
            ["git", "config", "--global", "--get", "user.name"],
            capture_output=True,
            check=False,
        ),
        call(
            ["git", "config", "--global", "--get", "user.email"],
            capture_output=True,
            check=False,
        ),
        call(["git", "config", "--global", "user.email", "a@example.invalid"]),
    ]


def test_empty_values(target):
    GitConfigEnsure(()).execute(target)
    target.runner.run.assert_not_called()
