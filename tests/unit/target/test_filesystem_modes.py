from pathlib import Path
from unittest.mock import call, create_autospec

import pytest

from phs.target.base import CommandResult, TargetCommandError
from phs.target.dryrun.dryrun_filesystem import DryRunFilesystem
from phs.target.filesystem import Filesystem, RunnerFilesystem
from phs.target.runner import Runner


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize(
    "current,mode,change",
    [
        ("700\n", 0o700, False),
        ("0600\n", 0o600, False),
        ("755\n", 0o700, True),
        ("644\n", 0o600, True),
    ],
)
def test_ensures_mode_only_when_different(root, current, mode, change):
    runner = create_autospec(Runner, instance=True)
    runner.run.return_value = CommandResult((), 0, current, None)
    RunnerFilesystem(runner).ensure_mode(Path("/managed/file space"), mode, root=root)
    expected = [
        call(
            ["stat", "-c", "%a", "--", "/managed/file space"],
            root=root,
            capture_output=True,
        )
    ]
    if change:
        expected.append(
            call(["chmod", f"{mode:04o}", "--", "/managed/file space"], root=root)
        )
    assert runner.run.call_args_list == expected


@pytest.mark.parametrize("mode", [-1, 0o10000])
def test_invalid_mode_never_runs_commands(mode):
    runner = create_autospec(Runner, instance=True)
    with pytest.raises(ValueError, match="File mode"):
        RunnerFilesystem(runner).ensure_mode(Path("/file"), mode)
    runner.run.assert_not_called()


@pytest.mark.parametrize(
    "stdout,error", [(None, RuntimeError), ("invalid", ValueError)]
)
def test_invalid_stat_output_does_not_chmod(stdout, error):
    runner = create_autospec(Runner, instance=True)
    runner.run.return_value = CommandResult((), 0, stdout, None)
    with pytest.raises(error):
        RunnerFilesystem(runner).ensure_mode(Path("/file"), 0o600)
    assert runner.run.call_count == 1


def test_stat_failure_does_not_chmod():
    runner = create_autospec(Runner, instance=True)
    runner.run.side_effect = TargetCommandError(CommandResult((), 1, None, None))
    with pytest.raises(TargetCommandError):
        RunnerFilesystem(runner).ensure_mode(Path("/file"), 0o600)
    assert runner.run.call_count == 1


@pytest.mark.parametrize("root", [False, True])
def test_dry_run_only_logs_permission_changes(root, capsys):
    filesystem = create_autospec(Filesystem, instance=True)
    filesystem.description = "remote"
    DryRunFilesystem(filesystem).ensure_mode(Path("/managed/file"), 0o600, root=root)
    assert (
        capsys.readouterr().out
        == f"[dry-run] [remote] {'sudo ' if root else ''}chmod 0600 /managed/file\n"
    )
    filesystem.ensure_mode.assert_not_called()
