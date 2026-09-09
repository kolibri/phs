from tests.vm.environment.lib.ssh import SSHClient

NFS_SOURCE = "192.168.76.2:/srv/phs-test"
NFS_TARGET = "/mnt/phs-test"


def test_nfs_server_is_active(fixture: SSHClient) -> None:
    result = fixture.run(
        ["systemctl", "is-active", "nfs-server.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "active"


def test_nfs_mount_is_real(sut: SSHClient) -> None:
    result = sut.run(
        [
            "findmnt",
            "--noheadings",
            "--raw",
            "--target",
            NFS_TARGET,
            "--output",
            "FSTYPE,SOURCE",
        ],
        capture_output=True,
    )
    filesystem, source = result.stdout.strip().split(maxsplit=1)
    assert filesystem in {"nfs", "nfs4"}
    assert source == NFS_SOURCE


def test_sut_can_write_to_nfs_server(
    sut: SSHClient,
    fixture: SSHClient,
) -> None:
    path = f"{NFS_TARGET}/written-by-sut"
    result = sut.run(["tee", path], input_text="hello from sut\n", check=False)
    assert result.returncode == 0

    server = fixture.run(
        ["cat", "/srv/phs-test/written-by-sut"],
        capture_output=True,
    )
    assert server.stdout == "hello from sut\n"
    sut.run(["rm", "-f", path])


def test_fixture_writes_are_visible_on_sut(
    sut: SSHClient,
    fixture: SSHClient,
) -> None:
    server_path = "/srv/phs-test/written-by-fixture"
    result = fixture.run(
        ["tee", server_path],
        input_text="hello from fixture\n",
        check=False,
    )
    assert result.returncode == 0

    client = sut.run(
        ["cat", f"{NFS_TARGET}/written-by-fixture"],
        capture_output=True,
    )
    assert client.stdout == "hello from fixture\n"
    fixture.run(["rm", "-f", server_path])
