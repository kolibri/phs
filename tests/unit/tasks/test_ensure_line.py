from pathlib import Path

import pytest

from phs.tasks.ensure_line import EnsureLine


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize(
    "before,after",
    [
        ("", "enabled=true\n"),
        ("other", "other\nenabled=true\n"),
        ("other\n", "other\nenabled=true\n"),
        ("enabled=false\nother\n", "enabled=true\nother\n"),
        ("other\r\nenabled=false\r\n", "other\r\nenabled=true\r\n"),
        ("enabled=false", "enabled=true"),
        ("enabled=false\nenabled=other\n", "enabled=true\nenabled=other\n"),
        ("enabled=true\n", None),
        ("enabled=true\r\n", None),
        ("enabled=true", None),
    ],
)
def test_ensures_first_matching_line_preserving_endings(target, root, before, after):
    path = Path("/etc/example.conf")
    target.filesystem.read_text.return_value = before
    EnsureLine(path, "enabled=true", match="^enabled=", root=root).execute(target)
    target.filesystem.read_text.assert_called_once_with(path, root=root)
    if after is None:
        target.filesystem.write_text.assert_not_called()
    else:
        target.filesystem.write_text.assert_called_once_with(path, after, root=root)


@pytest.mark.parametrize(
    "before,after",
    [
        ("a.b[0]\n", None),
        ("axb0\n", "axb0\na.b[0]\n"),
        ("prefix a.b[0]\n", "prefix a.b[0]\na.b[0]\n"),
    ],
)
def test_default_match_is_literal_and_anchored(target, before, after):
    path = Path("/srv/config")
    target.filesystem.read_text.return_value = before
    EnsureLine(path, "a.b[0]").execute(target)
    if after is None:
        target.filesystem.write_text.assert_not_called()
    else:
        target.filesystem.write_text.assert_called_once_with(path, after, root=False)
