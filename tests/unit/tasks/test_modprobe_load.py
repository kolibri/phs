from pathlib import Path
from unittest.mock import Mock, call

import pytest

from phs.tasks.modprobe_load import ModprobeLoad


@pytest.mark.parametrize("current", [None, "wrong\n", "nfs\n"])
def test_ensures_persistent_config_before_loading(target, current):
    path = Path("/etc/modules-load.d/phs-nfs.conf")
    target.filesystem.exists.return_value = current is not None
    target.filesystem.read_text.return_value = current
    operations = Mock()
    operations.attach_mock(target.filesystem.write_text, "write")
    operations.attach_mock(target.runner.run, "run")
    ModprobeLoad(("nfs",)).execute(target)
    target.filesystem.exists.assert_called_once_with(path, root=True)
    if current is None:
        target.filesystem.read_text.assert_not_called()
    else:
        target.filesystem.read_text.assert_called_once_with(path, root=True)
    expected = []
    if current != "nfs\n":
        expected.append(call.write(path, "nfs\n", root=True))
    expected.append(call.run(["modprobe", "nfs"], root=True))
    assert operations.mock_calls == expected


@pytest.mark.parametrize("modules", [(), ("nfs", "loop")])
def test_processes_all_modules_in_order(target, modules):
    target.filesystem.exists.return_value = False
    ModprobeLoad(modules).execute(target)
    assert target.runner.run.call_args_list == [
        call(["modprobe", module], root=True) for module in modules
    ]
    assert target.filesystem.write_text.call_args_list == [
        call(Path(f"/etc/modules-load.d/phs-{module}.conf"), f"{module}\n", root=True)
        for module in modules
    ]
