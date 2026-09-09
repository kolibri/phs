import pytest

from tests.vm.environment.lib.environment import create_environment
from tests.vm.environment.lib.ssh import SSHClient


@pytest.fixture(scope="session")
def sut() -> SSHClient:
    environment = create_environment()
    result = environment.sut.ssh.run(
        ["true"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "SUT VM is not reachable. Run the VM workflow with `./test.sh vm`.",
            pytrace=False,
        )
    return environment.sut.ssh


@pytest.fixture(scope="session")
def fixture() -> SSHClient:
    environment = create_environment()
    result = environment.fixture.ssh.run(
        ["true"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "Fixture VM is not reachable. Run the VM workflow with `./test.sh vm`.",
            pytrace=False,
        )
    return environment.fixture.ssh
