from unittest.mock import call

import pytest

from phs.tasks.printer_ensure import PrinterEnsure


@pytest.mark.parametrize(
    "code,stdout,configure",
    [
        (0, "device for office: ipp://printer/queue\n", False),
        (0, "device for office: ipp://old/queue", True),
        (1, "device for office: ipp://printer/queue", True),
        (0, None, True),
    ],
)
@pytest.mark.parametrize("default_state", ["disabled", "correct", "wrong", "missing"])
def test_ensures_printer_and_optional_default(
    target, result, code, stdout, configure, default_state
):
    responses = [result(code, stdout)]
    if configure:
        responses.append(result())
    default_output = {
        "correct": "system default destination: office\n",
        "wrong": "system default destination: other",
        "missing": None,
    }
    if default_state != "disabled":
        responses += [result(stdout=default_output[default_state]), result()]
    target.runner.run.side_effect = responses
    PrinterEnsure(
        "office", "ipp://printer/queue", default=default_state != "disabled"
    ).execute(target)
    expected = [
        call(["lpstat", "-v", "office"], root=True, capture_output=True, check=False)
    ]
    if configure:
        expected.append(
            call(
                [
                    "lpadmin",
                    "-p",
                    "office",
                    "-E",
                    "-v",
                    "ipp://printer/queue",
                    "-m",
                    "everywhere",
                ],
                root=True,
            )
        )
    if default_state != "disabled":
        expected.append(
            call(["lpstat", "-d"], root=True, capture_output=True, check=False)
        )
        if default_state != "correct":
            expected.append(call(["lpadmin", "-d", "office"], root=True))
    assert target.runner.run.call_args_list == expected
