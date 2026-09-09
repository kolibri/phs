from tests.vm.environment.lib.ssh import SSHClient


def test_nfs_fstab_entry_is_not_duplicated(sut: SSHClient) -> None:
    result = sut.run(
        [
            "grep",
            "-c",
            r"^192\.168\.76\.2:/srv/phs-test[[:space:]]",
            "/etc/fstab",
        ],
        capture_output=True,
    )
    assert result.stdout.strip() == "1"
