import importlib
import shlex
import subprocess
from pathlib import Path
from unittest.mock import call, create_autospec, patch

import pytest

from phs import cli
from phs.context import AppContext
from phs.execution import Execution, ExecutionFactory
from phs.inventory import HostData, HostDataLoader
from phs.output import Output
from phs.settings import Settings
from phs.ssh import SSHRunner, SSHTarget
from phs.target.base import CommandResult
from phs.target.remote.remote_runner import RemoteRunner
from phs.target.remote.remote_transfer import RemoteTransfer
from phs.template import TemplateRenderer

authorize_module = importlib.import_module("phs.commands.authorize")
LOOSE_OPTIONS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]


@pytest.fixture
def host_data():
    return HostData(
        hostname="phs-test",
        ip="192.0.2.1",
        ssh_port=2222,
        hdd="",
        username="alice",
        groupname="alice",
        homedir="/home/alice",
        git_user="Alice",
        git_email="alice@example.invalid",
        shell="/bin/sh",
    )


@pytest.fixture
def context(host_data):
    context = create_autospec(AppContext, instance=True)
    context.settings = Settings()
    context.output = create_autospec(Output, instance=True)
    context.inventory = create_autospec(HostDataLoader, instance=True)
    context.inventory.load.return_value = host_data
    return context


@pytest.mark.parametrize("loose", [False, True])
def test_remote_ssh_options_preserve_default_command(loose):
    runner = RemoteRunner(
        "192.0.2.1", "alice", port=2222, identity_file=Path("/keys/id"), loose_ssh=loose
    )
    with patch(
        "subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0, "", ""),
    ) as run:
        runner.run(["true"], capture_output=True)
    run.assert_called_once_with(
        [
            "ssh",
            "-p",
            "2222",
            "-i",
            "/keys/id",
            *(LOOSE_OPTIONS if loose else []),
            "alice@192.0.2.1",
            "true",
        ],
        input=None,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("loose", [False, True])
@pytest.mark.parametrize("root", [False, True])
def test_transfer_and_directory_creation_share_ssh_policy(loose, root):
    runner = RemoteRunner("192.0.2.1", "alice", port=2222, loose_ssh=loose)
    ssh_options = ["-p", "2222", *(LOOSE_OPTIONS if loose else [])]
    with (
        patch.object(Path, "exists", autospec=True, return_value=True),
        patch.object(Path, "is_dir", autospec=True, return_value=False),
        patch(
            "subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess([], 0),
        ) as run,
    ):
        RemoteTransfer(runner).transfer(
            Path("/source/file"), Path("/destination/file"), root=root, create_dirs=True
        )
    mkdir = ["mkdir", "-p", "--", "/destination"]
    if root:
        mkdir = ["sudo", "-n", "--", *mkdir]
    assert run.call_args_list == [
        call(
            ["ssh", *ssh_options, "alice@192.0.2.1", shlex.join(mkdir)],
            input=None,
            text=True,
            capture_output=False,
            check=False,
        ),
        call(
            [
                "rsync",
                "-a",
                "--protect-args",
                "-e",
                shlex.join(["ssh", *ssh_options]),
                *(["--rsync-path", "sudo -n -- rsync"] if root else []),
                "--",
                "/source/file",
                "alice@192.0.2.1:/destination/file",
            ],
            check=False,
        ),
    ]


@pytest.mark.parametrize("loose", [False, True])
@pytest.mark.parametrize("dry_run", [False, True])
def test_execution_factory_propagates_settings(context, loose, dry_run):
    context.settings = Settings(loose_ssh=loose)
    execution = ExecutionFactory.create(context, host="phs-test", dry_run=dry_run)
    runner = execution.target.runner
    transfer = execution.target.transfer
    if dry_run:
        runner = runner.runner
        transfer = transfer.transfer
    remote = runner.runner
    assert isinstance(remote, RemoteRunner)
    assert remote.loose_ssh is loose
    assert transfer.runner is remote
    assert remote.ssh_options() == ["-p", "2222", *(LOOSE_OPTIONS if loose else [])]


@pytest.mark.parametrize(
    "loose,init_loose", [(False, False), (True, False), (False, True)]
)
def test_global_cli_option_reaches_real_execution_factory(
    monkeypatch, host_data, loose, init_loose
):
    inventory = create_autospec(HostDataLoader, instance=True)
    inventory.load.return_value = host_data
    renderer = create_autospec(TemplateRenderer, instance=True)
    # Keep Cyclopts parsing real, but do not read the user's ~/.phs.yaml.
    monkeypatch.setattr(cli.app, "config", ())
    monkeypatch.setattr(cli.app.meta, "config", ())
    with (
        patch("phs.cli.HostDataLoader", autospec=True, return_value=inventory),
        patch.object(TemplateRenderer, "builtin", autospec=True, return_value=renderer),
        patch.object(
            TemplateRenderer, "from_directory", autospec=True, return_value=renderer
        ),
        patch("phs.commands.init.Executor.execute", autospec=True) as execute,
    ):
        cli.app.meta(
            [
                *(["--loose-ssh"] if loose else []),
                "--config-dir=/inventory",
                "init",
                *(["--loose-ssh"] if init_loose else []),
                "--host=phs-test",
            ],
            exit_on_error=False,
            result_action="return_value",
        )
    target = execute.call_args.args[1]
    assert target.runner.runner.loose_ssh is (loose or init_loose)
    assert target.transfer.runner is target.runner.runner
    inventory.load.assert_called_once_with("phs-test")


def test_init_command_option_reaches_execution_factory(monkeypatch, context):
    monkeypatch.setattr(cli.app, "config", ())
    command, bound, _ = cli.app.parse_args(
        ["init", "--loose-ssh", "--host=phs-test"], exit_on_error=False
    )
    with patch("phs.commands.init.Executor.execute", autospec=True) as execute:
        command(*bound.args, **bound.kwargs, context=context)
    target = execute.call_args.args[1]
    assert target.runner.runner.loose_ssh is True
    assert target.transfer.runner is target.runner.runner


@pytest.mark.parametrize("loose", [False, True])
def test_authorization_connections_use_selected_policy(target, host_data, loose):
    target.runner.run.return_value = CommandResult((), 0, None, None)
    assert authorize_module._can_connect(
        target, Path("/keys/id"), host_data, loose_ssh=loose
    )
    options = LOOSE_OPTIONS if loose else ["-o", "StrictHostKeyChecking=accept-new"]
    target.runner.run.assert_called_once_with(
        [
            "ssh",
            "-i",
            "/keys/id",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            *options,
            "-o",
            "ConnectTimeout=5",
            "-p",
            "2222",
            "alice@192.0.2.1",
            "true",
        ],
        capture_output=True,
        check=False,
    )
    with patch(
        "subprocess.run", autospec=True, return_value=subprocess.CompletedProcess([], 0)
    ) as run:
        assert authorize_module._install_public_key(
            "ssh-ed25519 public", host_data, loose_ssh=loose
        )
    assert run.call_args.args[0] == [
        "ssh",
        *options,
        "-o",
        "ConnectTimeout=10",
        "-p",
        "2222",
        "alice@192.0.2.1",
        "sh",
        "-s",
    ]


@pytest.mark.parametrize("loose", [False, True])
def test_authorize_propagates_settings_to_both_connection_paths(
    context, target, host_data, loose
):
    context.settings = Settings(loose_ssh=loose)
    source_data = host_data.model_copy(update={"hostname": "source"})
    execution = Execution(source_data, target)
    target.filesystem.read_text.return_value = "ssh-ed25519 public"
    with (
        patch.object(ExecutionFactory, "create", autospec=True, return_value=execution),
        patch.object(authorize_module.Executor, "execute", autospec=True),
        patch.object(
            authorize_module,
            "_inventory_hosts",
            autospec=True,
            return_value=["phs-test"],
        ),
        patch.object(
            authorize_module, "_can_connect", autospec=True, side_effect=[False, True]
        ) as probe,
        patch.object(
            authorize_module, "_install_public_key", autospec=True, return_value=True
        ) as install,
    ):
        authorize_module.authorize(context=context)
    assert (
        probe.call_args_list
        == [
            call(
                target, Path("/home/alice/.ssh/id_ed25519"), host_data, loose_ssh=loose
            )
        ]
        * 2
    )
    install.assert_called_once_with("ssh-ed25519 public", host_data, loose_ssh=loose)


def test_installer_ssh_retains_existing_loose_behavior():
    with patch(
        "subprocess.run", autospec=True, return_value=subprocess.CompletedProcess([], 0)
    ) as run:
        SSHRunner().run_script(SSHTarget("192.0.2.1", "root", 2222), "script")
    run.assert_called_once_with(
        ["ssh", "-p", "2222", *LOOSE_OPTIONS, "root@192.0.2.1", "bash", "-s"],
        input="script",
        text=True,
        check=True,
    )
