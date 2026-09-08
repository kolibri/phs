from unittest.mock import call

import pytest

from phs.tasks.service_enable import ServiceEnable


@pytest.mark.parametrize("start", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_enables_and_starts_only_as_needed(target, result, start, enabled, active):
    responses = [result(0 if enabled else 1)]
    if start:
        responses.append(result(0 if active else 3))
    responses.append(result())
    target.runner.run.side_effect = responses
    ServiceEnable(("example.service",), start=start).execute(target)
    expected = [
        call(
            ["systemctl", "is-enabled", "--quiet", "example.service"],
            root=True,
            capture_output=True,
            check=False,
        )
    ]
    if start:
        expected.append(
            call(
                ["systemctl", "is-active", "--quiet", "example.service"],
                root=True,
                capture_output=True,
                check=False,
            )
        )
    if not enabled or (start and not active):
        expected.append(
            call(
                [
                    "systemctl",
                    "enable",
                    *(["--now"] if start else []),
                    "example.service",
                ],
                root=True,
            )
        )
    assert target.runner.run.call_args_list == expected


def test_continues_after_correct_service(target, result):
    target.runner.run.side_effect = [result(), result(), result(1), result(3), result()]
    ServiceEnable(("first", "second")).execute(target)
    assert target.runner.run.call_args_list == [
        call(
            ["systemctl", "is-enabled", "--quiet", "first"],
            root=True,
            capture_output=True,
            check=False,
        ),
        call(
            ["systemctl", "is-active", "--quiet", "first"],
            root=True,
            capture_output=True,
            check=False,
        ),
        call(
            ["systemctl", "is-enabled", "--quiet", "second"],
            root=True,
            capture_output=True,
            check=False,
        ),
        call(
            ["systemctl", "is-active", "--quiet", "second"],
            root=True,
            capture_output=True,
            check=False,
        ),
        call(["systemctl", "enable", "--now", "second"], root=True),
    ]


def test_empty_services(target):
    ServiceEnable(()).execute(target)
    target.runner.run.assert_not_called()
