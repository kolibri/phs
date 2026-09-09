from tests.vm.environment.lib.ssh import SSHClient


def test_qtile_desktop_packages_are_installed(sut: SSHClient) -> None:
    for package in ("qtile", "greetd"):
        result = sut.run(
            ["pacman", "-Q", package],
            check=False,
            capture_output=True,
        )
        assert result.returncode == 0, f"{package} is not installed:\n{result.stderr}"


def test_greetd_is_enabled(sut: SSHClient) -> None:
    result = sut.run(
        ["systemctl", "is-enabled", "greetd.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "enabled"


def test_qtile_config_was_written(sut: SSHClient) -> None:
    result = sut.run(
        ["test", "-s", "/home/ko/.config/qtile/config.py"],
        check=False,
    )
    assert result.returncode == 0
