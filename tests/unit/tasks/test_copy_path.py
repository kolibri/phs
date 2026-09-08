from pathlib import Path

import pytest

from phs.tasks.copy_path import CopyPath


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize("create_dirs", [False, True])
@pytest.mark.parametrize("exclude", [(), (".git", "*.tmp")])
def test_forwards_transfer_options(target, root, create_dirs, exclude):
    source, destination = Path("/source with spaces"), Path("/srv/destination")
    CopyPath(source, destination, root, create_dirs, exclude).execute(target)
    target.transfer.transfer.assert_called_once_with(
        source, destination, root=root, create_dirs=create_dirs, exclude=exclude
    )
    target.runner.run.assert_not_called()
