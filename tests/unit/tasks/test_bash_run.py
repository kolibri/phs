import pytest

from phs.tasks.bash_run import BashRun


@pytest.mark.parametrize("root", [False, True])
def test_passes_script_verbatim(target, root):
    script = "echo '$HOME'\nprintf '%s' 'a b'\n"
    BashRun(script, root=root).execute(target)
    target.runner.run.assert_called_once_with(
        ["bash", "-s"], root=root, input_text=script
    )
