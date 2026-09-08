from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from phs.backup.base import BackupRsyncData, BackupSnapshotError
from phs.target.base import TargetCommandError
from phs.tasks.backup_snapshot_create import BackupSnapshotCreate


@pytest.fixture
def fingerprint():
    # This dependency reads the controller's manifest in binary mode. Replace
    # that I/O boundary, while retaining the task's actual validation logic.
    with patch.object(
        BackupRsyncData, "fingerprint_manifest", autospec=True, return_value="digest"
    ) as fingerprint:
        yield fingerprint


@pytest.fixture
def rsync():
    return BackupRsyncData(
        manifest_path=Path("/backup/manifest"),
        source_dir=Path("/source"),
        target_dir=Path("/snapshots"),
        name="snapshot",
        previous_dir=None,
        manifest_sha256="digest",
    )


def rsync_command(previous=None):
    return [
        "env",
        "LC_ALL=C",
        "rsync",
        "-aHAX",
        "--numeric-ids",
        "--from0",
        "--ignore-missing-args",
        "--info=progress2,stats2",
        "--files-from=/backup/manifest",
        *([] if previous is None else [f"--link-dest={previous}"]),
        "/source/",
        "/snapshots/.snapshot.partial/",
    ]


@pytest.mark.parametrize("returncode", [0, 24])
@pytest.mark.parametrize("stored", [None, " digest\n"])
@pytest.mark.parametrize("previous", [None, Path("/snapshots/previous")])
def test_validates_manifest_before_copy_and_finalizes_success(
    target, result, fingerprint, rsync, returncode, stored, previous
):
    rsync = replace(rsync, previous_dir=previous)
    target.filesystem.exists.return_value = stored is not None
    target.filesystem.read_text.return_value = stored
    target.runner.run.side_effect = [result(), result(returncode), result(), result()]
    operations = Mock()
    operations.attach_mock(target.runner.run, "run")
    operations.attach_mock(fingerprint, "fingerprint")
    operations.attach_mock(target.filesystem.exists, "exists")
    operations.attach_mock(target.filesystem.read_text, "read")
    operations.attach_mock(target.filesystem.write_text, "write")

    BackupSnapshotCreate(rsync, "alice", "backup").execute(target)

    expected = [
        call.run(
            [
                "install",
                "-d",
                "-o",
                "alice",
                "-g",
                "backup",
                "-m",
                "0750",
                "--",
                "/snapshots/.snapshot.partial",
            ],
            root=True,
        ),
        call.fingerprint(Path("/backup/manifest")),
        call.exists(Path("/snapshots/.snapshot.partial.manifest-sha256"), root=True),
    ]
    if stored is None:
        expected.append(
            call.write(
                Path("/snapshots/.snapshot.partial.manifest-sha256"),
                "digest\n",
                root=True,
            )
        )
    else:
        expected.append(
            call.read(Path("/snapshots/.snapshot.partial.manifest-sha256"), root=True)
        )
    expected.extend(
        [
            call.run(rsync_command(previous), root=True, check=False),
            call.run(
                ["mv", "--", "/snapshots/.snapshot.partial", "/snapshots/snapshot"],
                root=True,
            ),
            call.run(
                ["rm", "--", "/snapshots/.snapshot.partial.manifest-sha256"], root=True
            ),
        ]
    )
    assert operations.mock_calls == expected
    if returncode == 24:
        target.output.warning.assert_called_once()
    else:
        target.output.warning.assert_not_called()


@pytest.mark.parametrize("returncode", [1, 23, 25])
def test_failed_rsync_preserves_partial_snapshot_and_metadata(
    target, result, fingerprint, rsync, returncode
):
    target.filesystem.exists.return_value = True
    target.filesystem.read_text.return_value = "digest\n"
    failure = result(returncode)
    target.runner.run.side_effect = [result(), failure]
    with pytest.raises(TargetCommandError) as error:
        BackupSnapshotCreate(rsync, "alice", "backup").execute(target)
    assert error.value.result is failure
    assert target.runner.run.call_args_list == [
        call(
            [
                "install",
                "-d",
                "-o",
                "alice",
                "-g",
                "backup",
                "-m",
                "0750",
                "--",
                "/snapshots/.snapshot.partial",
            ],
            root=True,
        ),
        call(rsync_command(), root=True, check=False),
    ]
    target.filesystem.write_text.assert_not_called()


def test_changed_manifest_stops_before_rsync_or_metadata_changes(
    target, fingerprint, rsync
):
    fingerprint.return_value = "changed"
    with pytest.raises(BackupSnapshotError, match="changed after.*initialized"):
        BackupSnapshotCreate(rsync, "alice", "backup").execute(target)
    fingerprint.assert_called_once_with(Path("/backup/manifest"))
    assert target.filesystem.mock_calls == []
    target.runner.run.assert_called_once_with(
        [
            "install",
            "-d",
            "-o",
            "alice",
            "-g",
            "backup",
            "-m",
            "0750",
            "--",
            "/snapshots/.snapshot.partial",
        ],
        root=True,
    )


@pytest.mark.parametrize("stored", ["different\n", "", " \n"])
def test_mismatching_resume_metadata_stops_before_rsync(
    target, fingerprint, rsync, stored
):
    target.filesystem.exists.return_value = True
    target.filesystem.read_text.return_value = stored
    with pytest.raises(BackupSnapshotError, match="changed since the interrupted run"):
        BackupSnapshotCreate(rsync, "alice", "backup").execute(target)
    target.filesystem.exists.assert_called_once_with(
        rsync.manifest_sha256_path, root=True
    )
    target.filesystem.read_text.assert_called_once_with(
        rsync.manifest_sha256_path, root=True
    )
    target.filesystem.write_text.assert_not_called()
    target.runner.run.assert_called_once_with(
        [
            "install",
            "-d",
            "-o",
            "alice",
            "-g",
            "backup",
            "-m",
            "0750",
            "--",
            "/snapshots/.snapshot.partial",
        ],
        root=True,
    )
