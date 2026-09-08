import io
import shlex
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from phs.output import Output
from phs.target.base import CommandResult, TargetCommandError
from phs.target.dryrun.dryrun_runner import DryRunRunner
from phs.target.local.local_runner import LocalRunner
from phs.target.remote.remote_runner import RemoteRunner
from phs.target.runner import OutputRunner, Runner


@pytest.mark.parametrize("cwd", [None, Path("/target/build space")])
@pytest.mark.parametrize("capture", [False, True])
def test_local_runner_passes_cwd_to_subprocess(cwd, capture):
    completed = subprocess.CompletedProcess(["makepkg"], 0, "output", "errors")
    with patch(
        "phs.target.local.local_runner.subprocess.run",
        autospec=True,
        return_value=completed,
    ) as run:
        result = LocalRunner().run(
            ["makepkg"], cwd=cwd, input_text="input", capture_output=capture
        )
    run.assert_called_once_with(
        ["makepkg"],
        cwd=cwd,
        input="input",
        text=True,
        capture_output=capture,
        check=False,
    )
    assert result == CommandResult(
        ("makepkg",), 0, "output" if capture else None, "errors" if capture else None
    )


@pytest.mark.parametrize("cwd", [None, Path("/target/build")])
def test_local_streaming_passes_cwd(cwd):
    process = Mock(spec=subprocess.Popen)
    process.stdout = io.StringIO("one\ntwo\n")
    process.wait.return_value = 0
    callback = Mock()
    with patch(
        "phs.target.local.local_runner.subprocess.Popen",
        autospec=True,
        return_value=process,
    ) as popen:
        result = LocalRunner().run(["makepkg"], cwd=cwd, on_output=callback)
    popen.assert_called_once_with(
        ["makepkg"],
        cwd=cwd,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert [call.args for call in callback.call_args_list] == [("one",), ("two",)]
    assert result.returncode == 0


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize("cwd", [None, Path("/target/build")])
def test_local_root_behavior_is_preserved(root, cwd):
    with (
        patch("phs.target.local.local_runner.os.geteuid", return_value=1000),
        patch(
            "phs.target.local.local_runner.subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess([], 0),
        ) as run,
    ):
        LocalRunner().run(["tool"], root=root, cwd=cwd)
    assert run.call_args.args == (["sudo", "-n", "--", "tool"] if root else ["tool"],)
    assert run.call_args.kwargs["cwd"] == cwd


@pytest.mark.parametrize("root", [False, True])
@pytest.mark.parametrize(
    "cwd,quoted",
    [
        (None, None),
        (Path("/target/build"), "/target/build"),
        (Path("/target/a b;$(touch nope)"), "'/target/a b;$(touch nope)'"),
        (Path("/target/it's here"), "'/target/it'\"'\"'s here'"),
        (Path("-option"), "./-option"),
        (Path("relative dir"), "'./relative dir'"),
    ],
)
def test_remote_cwd_is_quoted_only_at_ssh_transport(root, cwd, quoted):
    runner = RemoteRunner(
        "example.invalid", "alice", port=2222, identity_file=Path("/keys/id")
    )
    argv = ["makepkg", "argument with 'quotes'; $HOME"]
    command_text = shlex.join(["sudo", "-n", "--", *argv] if root else argv)
    if quoted is not None:
        command_text = f"cd {quoted} && {command_text}"
    with patch(
        "phs.target.remote.remote_runner.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0, "output", ""),
    ) as run:
        result = runner.run(
            argv, cwd=cwd, root=root, capture_output=True, input_text="input"
        )
    expected = [
        "ssh",
        "-p",
        "2222",
        "-i",
        "/keys/id",
        "alice@example.invalid",
        command_text,
    ]
    # cwd belongs to the target command, not to the controller's SSH process.
    run.assert_called_once_with(
        expected, input="input", text=True, capture_output=True, check=False
    )
    assert result.command == tuple(expected)
    assert result.stdout == "output"


def test_remote_streaming_keeps_cwd_on_target():
    process = Mock(spec=subprocess.Popen)
    process.stdout = io.StringIO("built\n")
    process.wait.return_value = 0
    callback = Mock()
    with patch(
        "phs.target.remote.remote_runner.subprocess.Popen",
        autospec=True,
        return_value=process,
    ) as popen:
        RemoteRunner("example.invalid", "alice").run(
            ["makepkg"], cwd=Path("/target/build"), on_output=callback
        )
    popen.assert_called_once_with(
        ["ssh", "-p", "22", "alice@example.invalid", "cd /target/build && makepkg"],
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    callback.assert_called_once_with("built")


@pytest.mark.parametrize(
    "runner", [LocalRunner(), RemoteRunner("example.invalid", "alice")]
)
@pytest.mark.parametrize("check", [False, True])
def test_cwd_preserves_command_error_handling(runner, check):
    with patch(
        "subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 7, "", "failed"),
    ):
        if check:
            with pytest.raises(TargetCommandError) as error:
                runner.run(["makepkg"], cwd=Path("/build"), capture_output=True)
            assert error.value.result.returncode == 7
        else:
            assert (
                runner.run(
                    ["makepkg"], cwd=Path("/build"), capture_output=True, check=False
                ).returncode
                == 7
            )


@pytest.mark.parametrize("cwd", [None, Path("/build")])
@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("custom_callback", [False, True])
def test_output_runner_forwards_cwd_and_existing_options(cwd, capture, custom_callback):
    runner = Mock(spec=Runner)
    output = Mock(spec=Output)
    callback = Mock() if custom_callback else None
    result = OutputRunner(runner, output).run(
        ["makepkg"],
        root=True,
        cwd=cwd,
        capture_output=capture,
        check=False,
        input_text="input",
        on_output=callback,
    )
    kwargs = {"root": True, "cwd": cwd, "input_text": "input", "check": False}
    if capture:
        kwargs["capture_output"] = True
    else:
        kwargs["on_output"] = callback if custom_callback else output.text
    runner.run.assert_called_once_with(["makepkg"], **kwargs)
    assert result is runner.run.return_value


@pytest.mark.parametrize("cwd", [None, Path("/remote/build space")])
def test_dry_runner_logs_cwd_without_execution(capsys, cwd):
    runner = Mock(spec=Runner)
    runner.description = "ssh alice@example.invalid:22"
    dry_runner = DryRunRunner(runner)
    result = dry_runner.run(["makepkg"], root=True, cwd=cwd, input_text="input")
    expected = "[dry-run] [ssh alice@example.invalid:22] sudo makepkg\n"
    if cwd is not None:
        expected += f"[dry-run] cwd: {cwd}\n"
    expected += "[dry-run] stdin:\ninput\n"
    assert capsys.readouterr().out == expected
    assert result.returncode == 0
    runner.run.assert_not_called()


def test_dry_run_status_survives_output_wrapper():
    local = LocalRunner()
    remote = RemoteRunner("example.invalid", "alice")
    output = Mock(spec=Output)
    assert local.dry_run is False
    assert remote.dry_run is False
    assert OutputRunner(local, output).dry_run is False
    assert OutputRunner(DryRunRunner(remote), output).dry_run is True
