import pytest

from phs.target.base import CommandResult


@pytest.fixture
def result():
    def make(returncode=0, stdout=None):
        return CommandResult(("test-command",), returncode, stdout, None)

    return make


@pytest.fixture(autouse=True)
def forbid_processes(monkeypatch):
    """Fail immediately if a task bypasses its mocked runner."""

    def forbidden(*args, **kwargs):
        pytest.fail("Task unit tests must not launch processes")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("os.system", forbidden)
