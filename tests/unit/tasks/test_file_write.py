from pathlib import Path
from unittest.mock import call

import pytest

from phs.tasks.file_write import FileWrite
from phs.watch import WatchedFile

PATH = Path("/etc/example.conf")


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize("actual", [None, "old\n", "desired\n"])
def test_unwatched_state_transitions(target, root, actual):
    target.filesystem.exists.return_value = actual is not None
    target.filesystem.read_text.return_value = actual
    FileWrite(PATH, "desired", root=root).execute(target)
    target.filesystem.exists.assert_called_once_with(PATH, root=root)
    if actual is None:
        target.filesystem.read_text.assert_not_called()
    else:
        target.filesystem.read_text.assert_called_once_with(PATH, root=root)
    if actual == "desired\n":
        target.filesystem.write_text.assert_not_called()
    else:
        target.filesystem.write_text.assert_called_once_with(
            PATH, "desired\n", root=root
        )
    assert target.watch.mock_calls == []


@pytest.mark.parametrize(
    "content,as_given,expected",
    [
        ("\n    one\n      two\n", False, "one\n  two\n"),
        ("", False, "\n"),
        ("  one\r\n\n", True, "  one\r\n\n"),
        ("", True, ""),
    ],
)
def test_content_normalization(target, content, as_given, expected):
    target.filesystem.exists.return_value = False
    FileWrite(PATH, content, as_given=as_given).execute(target)
    target.filesystem.write_text.assert_called_once_with(PATH, expected, root=False)


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize(
    "actual,cached,write",
    [
        ("desired\n", None, False),
        ("desired\n", "old\n", False),
        (None, None, True),
        ("old\n", "old\n", True),
    ],
)
def test_uncontested_watched_states_record_desired_content(
    target, root, actual, cached, write
):
    target.filesystem.exists.return_value = actual is not None
    target.filesystem.read_text.return_value = actual
    target.watch.get.return_value = (
        None if cached is None else WatchedFile(content=cached)
    )
    FileWrite(PATH, "desired", root=root, watched=True).execute(target)
    target.watch.get.assert_called_once_with(PATH)
    target.filesystem.exists.assert_called_once_with(PATH, root=root)
    if actual is None:
        target.filesystem.read_text.assert_not_called()
    else:
        target.filesystem.read_text.assert_called_once_with(PATH, root=root)
    if write:
        target.filesystem.write_text.assert_called_once_with(
            PATH, "desired\n", root=root
        )
    else:
        target.filesystem.write_text.assert_not_called()
    target.watch.record.assert_called_once_with(PATH, "desired\n", root=root)
    target.watch.show_diff.assert_not_called()
    target.output.prompt.assert_not_called()


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize(
    "force,answers,write",
    [(False, ["k"], False), (False, ["r", "invalid", " A "], True), (True, [], True)],
)
def test_existing_uncached_file_requires_choice_unless_forced(
    target, root, force, answers, write
):
    target.filesystem.exists.return_value = True
    target.filesystem.read_text.return_value = "local\n"
    target.watch.get.return_value = None
    target.watch.force = force
    target.output.prompt.side_effect = answers
    FileWrite(PATH, "desired", root=root, watched=True).execute(target)
    target.watch.show_diff.assert_called_once_with(
        PATH, "local\n", "desired\n", before_name="actual", after_name="desired"
    )
    assert target.output.prompt.call_count == len(answers)
    if write:
        target.filesystem.write_text.assert_called_once_with(
            PATH, "desired\n", root=root
        )
        target.watch.record.assert_called_once_with(PATH, "desired\n", root=root)
    else:
        target.filesystem.write_text.assert_not_called()
        target.watch.record.assert_not_called()
    target.watch.preserve.assert_not_called()


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize("actual", [None, "local\n"])
@pytest.mark.parametrize(
    "desired,force,answers,action",
    [
        ("cached\n", False, ["k"], "keep"),
        ("cached\n", False, ["a", " R "], "restore"),
        ("cached\n", True, [], "restore"),
        ("new\n", False, ["k"], "keep"),
        ("new\n", False, ["r"], "restore"),
        ("new\n", False, ["a"], "apply"),
        ("new\n", True, [], "apply"),
    ],
)
def test_watched_conflict_choices(
    target, root, actual, desired, force, answers, action
):
    target.filesystem.exists.return_value = actual is not None
    target.filesystem.read_text.return_value = actual
    target.watch.get.return_value = WatchedFile(content="cached\n")
    target.watch.force = force
    target.output.prompt.side_effect = answers
    FileWrite(PATH, desired, root=root, watched=True).execute(target)
    differences = [
        call(PATH, "cached\n", actual or "", before_name="cached", after_name="actual")
    ]
    if desired != "cached\n":
        differences.append(
            call(PATH, "cached\n", desired, before_name="cached", after_name="desired")
        )
    assert target.watch.show_diff.call_args_list == differences
    assert target.output.prompt.call_count == len(answers)
    if action == "keep":
        target.watch.preserve.assert_called_once_with(PATH)
        target.filesystem.write_text.assert_not_called()
        target.watch.record.assert_not_called()
    else:
        content = "cached\n" if action == "restore" else desired
        target.filesystem.write_text.assert_called_once_with(PATH, content, root=root)
        target.watch.record.assert_called_once_with(PATH, content, root=root)
        target.watch.preserve.assert_not_called()
