import time

from tests.vm.environment.lib.ssh import SSHClient

PRINTER_NAME = "test-printer"
PRINTER_URI = "ipp://192.168.76.2:8000/ipp/print"
SPOOL = "/var/spool/phs-test-printer"


def spool_files(fixture: SSHClient) -> set[str]:
    result = fixture.run(
        [
            "find",
            SPOOL,
            "-maxdepth",
            "1",
            "-type",
            "f",
            "-printf",
            "%f\\n",
        ],
        capture_output=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def test_fake_printer_service_is_active(fixture: SSHClient) -> None:
    result = fixture.run(
        ["systemctl", "is-active", "phs-test-printer.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "active"


def test_cups_is_running_on_sut(sut: SSHClient) -> None:
    result = sut.run(
        ["systemctl", "is-active", "cups.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "active"


def test_avahi_is_running_on_sut(sut: SSHClient) -> None:
    result = sut.run(
        ["systemctl", "is-active", "avahi-daemon.service"],
        capture_output=True,
    )
    assert result.stdout.strip() == "active"


def test_printer_has_expected_uri(sut: SSHClient) -> None:
    result = sut.run(
        ["lpstat", "-v", PRINTER_NAME],
        capture_output=True,
    )
    assert result.stdout.strip() == f"device for {PRINTER_NAME}: {PRINTER_URI}"


def test_printer_is_default(sut: SSHClient) -> None:
    result = sut.run(["lpstat", "-d"], capture_output=True)
    assert result.stdout.strip() == f"system default destination: {PRINTER_NAME}"


def test_real_print_job_reaches_fixture(
    sut: SSHClient,
    fixture: SSHClient,
) -> None:
    before = spool_files(fixture)

    result = sut.run(
        ["lp", "-d", PRINTER_NAME, "/etc/hostname"],
        capture_output=True,
    )
    assert f"request id is {PRINTER_NAME}-" in result.stdout

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        after = spool_files(fixture)
        if after - before:
            return
        time.sleep(0.25)

    raise AssertionError("print job did not reach the fixture spool")
