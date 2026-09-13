from pathlib import Path
from unittest.mock import create_autospec, patch

import pytest

from phs.commands.setup import MODULES, _select_modules, setup_app
from phs.context import AppContext
from phs.execution import Execution, ExecutionFactory
from phs.inventory import HostData, HostDataLoader
from phs.inventory.config import SshHostConfig
from phs.modules.setup.ssh_config import SshConfig
from phs.output import Output
from phs.settings import Settings
from phs.target.base import CommandResult
from phs.target.remote.remote_runner import RemoteRunner
from phs.tasks.ssh_config_ensure import SshConfigEnsure


@pytest.fixture
def data():
    return HostData(
        hostname="workstation",
        ip="192.0.2.1",
        ssh_port=22,
        hdd="",
        username="ko",
        groupname="ko",
        homedir="/managed/ko",
        git_user="Ko",
        git_email="ko@example.invalid",
        shell="/bin/sh",
        modules=["ssh-config"],
        ssh_config={"cid.ko": SshHostConfig(hostname="cid.ko", port=2222)},
    )


@pytest.fixture
def context(data):
    context = create_autospec(AppContext, instance=True)
    context.output = create_autospec(Output, instance=True)
    context.settings = Settings()
    context.inventory = create_autospec(HostDataLoader, instance=True)
    context.inventory.load.return_value = data
    return context


def test_module_uses_managed_home_and_inventory_values(context, data):
    assert SshConfig().tasks(context, data) == [
        SshConfigEnsure(
            Path("/managed/ko"),
            (("cid.ko", SshHostConfig(hostname="cid.ko", port=2222)),),
        )
    ]
    assert isinstance(MODULES["ssh-config"], SshConfig)
    assert _select_modules(["ssh-config"], set()) == [MODULES["ssh-config"]]


@pytest.mark.parametrize(
    "tokens", [["ssh-config", "--host=workstation"], ["--host=workstation"]]
)
def test_setup_subcommand_and_configured_module_execute_real_task(
    context, data, target, tokens
):
    target.filesystem.exists.return_value = False
    command, bound, _ = setup_app.parse_args(tokens, exit_on_error=False)
    with patch.object(
        ExecutionFactory, "create", autospec=True, return_value=Execution(data, target)
    ) as factory:
        command(*bound.args, **bound.kwargs, context=context)
    factory.assert_called_once_with(context, host="workstation", dry_run=False)
    writes = {
        item.args[0]: item.args[1]
        for item in target.filesystem.write_text.call_args_list
    }
    assert writes[Path("/managed/ko/.ssh/config")] == "Include ~/.ssh/config.d/*\n"
    assert (
        "Host cid.ko\n    HostName cid.ko\n    Port 2222\n"
        in writes[Path("/managed/ko/.ssh/config.d/phs")]
    )
    target.watch.save.assert_called_once_with(success=True)


def test_dry_run_uses_standard_factory_wrappers_and_never_mutates_target(
    context, capsys
):
    remote = create_autospec(RemoteRunner, instance=True)
    remote.description = "remote workstation"
    remote.run.return_value = CommandResult((), 1, "", "")
    command, bound, _ = setup_app.parse_args(
        ["ssh-config", "--host=workstation", "--dry-run"], exit_on_error=False
    )
    with patch("phs.execution.RemoteRunner", autospec=True, return_value=remote):
        command(*bound.args, **bound.kwargs, context=context)
    assert remote.run.call_args_list
    assert all(item.args[0][:2] == ["test", "-e"] for item in remote.run.call_args_list)
    output = capsys.readouterr().out
    assert "chmod 0700 /managed/ko/.ssh" in output
    assert "write /managed/ko/.ssh/config.d/phs" in output
    assert "write /managed/ko/.ssh/config" in output
