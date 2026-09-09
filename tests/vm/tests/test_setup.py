from tests.vm.environment.lib.ssh import SSHClient


def test_packages_are_installed(sut: SSHClient) -> None:
    for package in ("nano", "git", "tig", "less"):
        result = sut.run(
            ["pacman", "-Q", package],
            check=False,
            capture_output=True,
        )
        assert result.returncode == 0, f"{package} is not installed:\n{result.stderr}"


def test_git_identity_is_configured(sut: SSHClient) -> None:
    name = sut.run(
        ["git", "config", "--global", "--get", "user.name"],
        capture_output=True,
    )
    email = sut.run(
        ["git", "config", "--global", "--get", "user.email"],
        capture_output=True,
    )

    assert name.stdout.strip() == "PHS VM Test"
    assert email.stdout.strip() == "phs-vm@example.invalid"


def test_local_phs_is_installed(sut: SSHClient) -> None:
    result = sut.run(["phs", "--help"], check=False, capture_output=True)
    assert result.returncode == 0


def test_local_checkout_still_has_git_origin(sut: SSHClient) -> None:
    result = sut.run(
        [
            "git",
            "-C",
            "/home/ko/projects/phs",
            "remote",
            "get-url",
            "origin",
        ],
        capture_output=True,
    )
    assert result.stdout.strip() == "https://github.com/kolibri/phs.git"
