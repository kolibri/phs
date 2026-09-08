from pathlib import Path
from unittest.mock import Mock, call

import pytest

from phs.backup.manifest import BackupManifest
from phs.tasks.backup_manifest_write import BackupManifestWrite


@pytest.mark.parametrize(
    "paths,content", [([], ""), ([Path("a b"), Path("dir/file")], "a b\0dir/file\0")]
)
def test_creates_parent_before_writing_null_delimited_manifest(target, paths, content):
    operations = Mock()
    operations.attach_mock(target.runner.run, "run")
    operations.attach_mock(target.filesystem.write_text, "write")
    path = Path("/backup/manifests/current")
    BackupManifestWrite(BackupManifest(paths), path).execute(target)
    assert operations.mock_calls == [
        call.run(["mkdir", "-p", "/backup/manifests"], root=True),
        call.write(path, content, root=True),
    ]
