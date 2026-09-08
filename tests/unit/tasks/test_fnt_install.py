from unittest.mock import call

import pytest

from phs.tasks.fnt_install import FntInstall


@pytest.mark.parametrize(
    "font,search",
    [
        ("google-Roboto", "Roboto"),
        ("fonts-dejavu", "dejavu"),
        ("custom-font", "custom-font"),
    ],
)
def test_searches_normalized_name_and_installs_exact_match(
    target, result, font, search
):
    target.runner.run.return_value = result(
        stdout=f"\n  {font}  \nother-font\n{font}\n"
    )
    FntInstall((font,)).execute(target)
    assert target.runner.run.call_args_list == [
        call(["fnt", "search", search], capture_output=True),
        call(["fnt", "install", font]),
    ]


@pytest.mark.parametrize("stdout", [None, "", "google-RobotoMono\n", "Roboto"])
def test_rejects_missing_exact_catalog_match(target, result, stdout):
    target.runner.run.return_value = result(stdout=stdout)
    with pytest.raises(ValueError, match="Font google-Roboto not found"):
        FntInstall(("google-Roboto", "later")).execute(target)
    target.runner.run.assert_called_once_with(
        ["fnt", "search", "Roboto"], capture_output=True
    )


@pytest.mark.parametrize("fonts", [(), ("one", "two")])
def test_processes_fonts_in_order(target, result, fonts):
    target.runner.run.return_value = result(stdout="one\ntwo\n")
    FntInstall(fonts).execute(target)
    assert target.runner.run.call_args_list == [
        command
        for font in fonts
        for command in (
            call(["fnt", "search", font], capture_output=True),
            call(["fnt", "install", font]),
        )
    ]
