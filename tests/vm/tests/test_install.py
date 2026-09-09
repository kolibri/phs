from tests.vm.environment.lib.ssh import SSHClient


def test_hostname(sut: SSHClient) -> None:
    result = sut.run(["hostnamectl", "--static"], capture_output=True)
    assert result.stdout.strip() == "phs-test"


def test_user_exists(sut: SSHClient) -> None:
    result = sut.run(["id", "ko"], check=False, capture_output=True)
    assert result.returncode == 0
    assert "uid=" in result.stdout


def test_passwordless_sudo_is_available(sut: SSHClient) -> None:
    result = sut.run(["sudo", "-n", "true"], check=False)
    assert result.returncode == 0


def test_sshd_is_enabled(sut: SSHClient) -> None:
    result = sut.run(
        ["systemctl", "is-enabled", "sshd.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "enabled"
