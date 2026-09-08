from unittest.mock import call, patch

import pytest

from phs.tasks.file_association_ensure import FileAssociationEnsure


@pytest.fixture
def mime_lookup():
    # The stdlib lookup can load /etc/mime.types or the Windows registry.
    with patch(
        "phs.tasks.file_association_ensure.guess_file_type",
        autospec=True,
        return_value=("text/plain", None),
    ) as lookup:
        yield lookup


@pytest.mark.parametrize("extension", ["txt", ".txt"])
@pytest.mark.parametrize(
    "current", [None, "", "other.desktop\n", " editor.desktop \nignored.desktop\n"]
)
def test_sets_missing_or_different_association(
    target, result, mime_lookup, extension, current
):
    target.runner.run.side_effect = [
        result(stdout="warning\n editor.desktop \nsecond.desktop\n"),
        result(stdout=current),
        result(),
    ]
    FileAssociationEnsure(((extension, "editor"),)).execute(target)
    mime_lookup.assert_called_once_with("file.txt")
    expected = [
        call(["mimeo", "--app2desk", "editor"], capture_output=True),
        call(["mimeo", "--mime2desk", "text/plain"], capture_output=True, check=False),
    ]
    if current is None or "editor.desktop" not in current:
        expected.append(call(["mimeo", "--prefer", "text/plain", "editor.desktop"]))
    assert target.runner.run.call_args_list == expected


@pytest.mark.parametrize("stdout", [None, "", "warning\nfile.desktop.bak\n"])
def test_missing_desktop_file_stops_before_querying_preferences(
    target, result, mime_lookup, stdout
):
    target.runner.run.return_value = result(stdout=stdout)
    with pytest.raises(RuntimeError, match="Could not find desktop file"):
        FileAssociationEnsure((("txt", "editor"),)).execute(target)
    target.runner.run.assert_called_once_with(
        ["mimeo", "--app2desk", "editor"], capture_output=True
    )


def test_unknown_extension_stops_before_commands(target, mime_lookup):
    mime_lookup.return_value = (None, None)
    with pytest.raises(ValueError, match="Could not determine MIME type.*unknown"):
        FileAssociationEnsure(((".unknown", "editor"),)).execute(target)
    target.runner.run.assert_not_called()


def test_continues_after_correct_association(target, result, mime_lookup):
    target.runner.run.side_effect = [
        result(stdout="first.desktop"),
        result(stdout="first.desktop"),
        result(stdout="second.desktop"),
        result(1),
        result(),
    ]
    FileAssociationEnsure((("txt", "first"), ("txt", "second"))).execute(target)
    assert target.runner.run.call_args_list == [
        call(["mimeo", "--app2desk", "first"], capture_output=True),
        call(["mimeo", "--mime2desk", "text/plain"], capture_output=True, check=False),
        call(["mimeo", "--app2desk", "second"], capture_output=True),
        call(["mimeo", "--mime2desk", "text/plain"], capture_output=True, check=False),
        call(["mimeo", "--prefer", "text/plain", "second.desktop"]),
    ]


def test_empty_associations(target, mime_lookup):
    FileAssociationEnsure(()).execute(target)
    mime_lookup.assert_not_called()
    target.runner.run.assert_not_called()
