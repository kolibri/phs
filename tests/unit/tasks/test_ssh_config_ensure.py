from pathlib import Path
from unittest.mock import call

import pytest

from phs.inventory.config import SshHostConfig
from phs.ssh_config import INCLUDE, render_ssh_config
from phs.tasks.ssh_config_ensure import SshConfigEnsure

HOME = Path("/managed/ko")
CONFIG = HOME / ".ssh/config"
MANAGED = HOME / ".ssh/config.d/phs"
HOSTS = (("cid.ko", SshHostConfig(hostname="cid.ko", port=2222)),)


@pytest.fixture
def files(target):
    files = {}
    target.filesystem.exists.side_effect = lambda path, **kwargs: path in files
    target.filesystem.read_text.side_effect = lambda path, **kwargs: files[path]
    target.filesystem.write_text.side_effect = lambda path, content, **kwargs: (
        files.__setitem__(path, content)
    )
    return files


def test_creates_directories_files_and_secure_permissions(target, files):
    SshConfigEnsure(HOME, HOSTS).execute(target)
    assert target.runner.run.call_args_list == [
        call(["mkdir", "-p", "--", "/managed/ko/.ssh"], root=False),
        call(["mkdir", "-p", "--", "/managed/ko/.ssh/config.d"], root=False),
    ]
    assert files == {CONFIG: INCLUDE + "\n", MANAGED: render_ssh_config(dict(HOSTS))}
    assert target.filesystem.ensure_mode.call_args_list == [
        call(HOME / ".ssh", 0o700),
        call(HOME / ".ssh/config.d", 0o700),
        call(MANAGED, 0o600),
        call(CONFIG, 0o600),
    ]
    target.watch.get.assert_not_called()
    target.output.prompt.assert_not_called()


@pytest.mark.parametrize(
    "original",
    [
        "Host github.com\n    IdentityFile ~/.ssh/github\n",
        "# personal\n\nHost foo\n    HostName foo.example",
        "# Include ~/.ssh/config.d/*\n",
    ],
)
def test_preserves_existing_user_content_and_second_run_does_not_write(
    target, files, original
):
    files[CONFIG] = original
    task = SshConfigEnsure(HOME, HOSTS)
    task.execute(target)
    assert files[CONFIG] == INCLUDE + "\n\n" + original
    target.filesystem.write_text.reset_mock()
    task.execute(target)
    target.filesystem.write_text.assert_not_called()


def test_unchanged_managed_file_and_include_are_not_written(target, files):
    files.update(
        {CONFIG: INCLUDE + "\n\nHost foo\n", MANAGED: render_ssh_config(dict(HOSTS))}
    )
    SshConfigEnsure(HOME, HOSTS).execute(target)
    target.filesystem.write_text.assert_not_called()


def test_changed_and_removed_hosts_replace_only_managed_file(target, files):
    files.update(
        {CONFIG: INCLUDE + "\n# personal\n", MANAGED: "Host old\n    User old\n"}
    )
    SshConfigEnsure(HOME, ()).execute(target)
    target.filesystem.write_text.assert_called_once_with(
        MANAGED, render_ssh_config({}), root=False
    )
    assert files[CONFIG] == INCLUDE + "\n# personal\n"


@pytest.mark.parametrize("home", [Path("relative"), Path("/managed/../elsewhere")])
def test_rejects_unsafe_home_before_side_effects(target, home):
    with pytest.raises(ValueError, match="home directory"):
        SshConfigEnsure(home, HOSTS).execute(target)
    assert target.filesystem.mock_calls == []
    target.runner.run.assert_not_called()


def test_duplicate_aliases_fail_before_side_effects(target):
    with pytest.raises(ValueError, match="Duplicate"):
        SshConfigEnsure(HOME, HOSTS + HOSTS).execute(target)
    target.runner.run.assert_not_called()
    assert target.filesystem.mock_calls == []


def test_invalid_include_does_not_partially_write_files(target, files):
    files[CONFIG] = 'Include "unterminated\n'
    with pytest.raises(ValueError, match="Include"):
        SshConfigEnsure(HOME, HOSTS).execute(target)
    target.runner.run.assert_not_called()
    target.filesystem.write_text.assert_not_called()
    target.filesystem.ensure_mode.assert_not_called()


def test_values_are_file_content_not_shell_commands(target, files):
    hosts = (("cid.ko", SshHostConfig(hostname="hojo.ko;$(do-not-run)")),)
    SshConfigEnsure(HOME, hosts).execute(target)
    assert "HostName hojo.ko;$(do-not-run)\n" in files[MANAGED]
    assert all("shell" not in item.kwargs for item in target.runner.run.call_args_list)
    assert set(files) == {CONFIG, MANAGED}
