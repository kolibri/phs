from __future__ import annotations

import os
import re
import socket
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TextIO

from . import check_kvm_access, die, log, require_command, require_file
from .ssh import SSHClient

_LINK_RE = re.compile(
    r"^\d+:\s+(?P<name>[^:]+):.*\blink/ether\s+(?P<mac>[0-9a-f:]+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class VMConfig:
    name: str
    disk: Path
    ovmf_code: Path
    ovmf_vars: Path
    ovmf_vars_template: Path
    monitor: Path
    pidfile: Path
    ssh_port: int
    ssh_timeout: float
    cpus: int
    memory_mib: int
    wan_mac: str
    testnet_mac: str
    serial: str
    has_graphics: bool
    testnet_role: str
    ssh_user: str


@dataclass(frozen=True, slots=True)
class VM:
    config: VMConfig
    network: TestNetwork

    @property
    def disk(self) -> Path:
        return self.config.disk

    @property
    def ovmf_vars(self) -> Path:
        return self.config.ovmf_vars

    @property
    def ssh_port(self) -> int:
        return self.config.ssh_port

    @property
    def ssh(self) -> SSHClient:
        return SSHClient(
            port=self.config.ssh_port,
            user=self.config.ssh_user,
            availability_timeout=self.config.ssh_timeout,
        )

    def ssh_as(self, user: str) -> SSHClient:
        return SSHClient(
            port=self.config.ssh_port,
            user=user,
            availability_timeout=self.config.ssh_timeout,
        )

    def pid(self) -> int | None:
        try:
            value = int(self.config.pidfile.read_text().strip())
        except FileNotFoundError, ValueError:
            return None
        return value if value > 0 else None

    @staticmethod
    def pid_is_running(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def is_running(self) -> bool:
        pid = self.pid()
        return pid is not None and self.pid_is_running(pid)

    def assert_stopped(self) -> None:
        if self.is_running():
            die(f"{self.config.name} is already running")
        self.config.pidfile.unlink(missing_ok=True)
        self.config.monitor.unlink(missing_ok=True)

    def check_requirements(self, *, installer: bool = False) -> None:
        for command in (
            "qemu-system-x86_64",
            "qemu-img",
            "ssh",
            "git",
            "tar",
        ):
            require_command(command)

        if installer:
            require_command("xorriso")

        require_file(self.config.ovmf_code)
        require_file(self.config.ovmf_vars_template)
        check_kvm_access()

    def qemu_args(
        self,
        *,
        installer_iso: Path | None = None,
        cloud_init_iso: Path | None = None,
        gui: bool = False,
    ) -> list[str]:
        # gui = True
        args = [
            "qemu-system-x86_64",
            "-name",
            self.config.name,
            "-machine",
            "q35,accel=kvm",
            "-cpu",
            "host",
            "-smp",
            str(self.config.cpus),
            "-m",
            str(self.config.memory_mib),
            "-drive",
            f"if=pflash,format=raw,readonly=on,file={self.config.ovmf_code}",
            "-drive",
            f"if=pflash,format=raw,file={self.config.ovmf_vars}",
            "-drive",
            f"if=none,id=osdisk,format=qcow2,file={self.config.disk}",
            "-device",
            f"nvme,drive=osdisk,serial={self.config.serial}",
            "-netdev",
            (f"user,id=wan,hostfwd=tcp:127.0.0.1:{self.config.ssh_port}-:22"),
            "-device",
            f"virtio-net-pci,netdev=wan,mac={self.config.wan_mac}",
            *self.network.qemu_args(
                self.config.testnet_role,
                self.config.testnet_mac,
            ),
            "-monitor",
            f"unix:{self.config.monitor},server=on,wait=off",
            # "-serial",
            # "stdio",
            "-pidfile",
            str(self.config.pidfile),
        ]

        if self.config.has_graphics:
            args += ["-vga", "virtio"]

        if installer_iso is not None:
            if cloud_init_iso is None:
                raise ValueError("installer boot requires cloud-init ISO")
            args += [
                "-drive",
                (
                    f"file={installer_iso},if=ide,index=2,"
                    "media=cdrom,readonly=on,id=archiso"
                ),
                "-drive",
                (
                    f"file={cloud_init_iso},if=ide,index=3,"
                    "media=cdrom,readonly=on,id=cloudinit"
                ),
                "-boot",
                "once=d",
            ]

        args += ["-display", "gtk"] if gui else ["-display", "none", "-daemonize"]
        # args += ["-display", "gtk"] if gui else ["-display", "none"]
        return args

    def boot(
        self,
        *,
        installer_iso: Path | None = None,
        cloud_init_iso: Path | None = None,
        gui: bool = False,
    ) -> None:
        self.check_requirements(installer=installer_iso is not None)
        require_file(self.config.disk)
        require_file(self.config.ovmf_vars)

        if installer_iso is not None:
            require_file(installer_iso)
        if cloud_init_iso is not None:
            require_file(cloud_init_iso)

        if self.is_running():
            if gui:
                die(f"{self.config.name} is already running; stop it before GUI boot")
            print(f"{self.config.name} is already running")
            return

        self.config.pidfile.unlink(missing_ok=True)
        self.config.monitor.unlink(missing_ok=True)
        if self.config.testnet_role == "server":
            self.network.cleanup_server_socket()

        log(f"booting {self.config.name}{' with GUI' if gui else ''}")
        subprocess.run(
            self.qemu_args(
                installer_iso=installer_iso,
                cloud_init_iso=cloud_init_iso,
                gui=gui,
            ),
            check=True,
        )

        if gui:
            self.config.pidfile.unlink(missing_ok=True)
            self.config.monitor.unlink(missing_ok=True)

    def send_monitor_command(self, command: str) -> None:
        if not self.config.monitor.exists():
            return
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.settimeout(2)
            connection.connect(str(self.config.monitor))
            connection.sendall(f"{command}\n".encode())
        except OSError:
            pass
        finally:
            connection.close()

    @classmethod
    def wait_for_process_exit(cls, pid: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not cls.pid_is_running(pid):
                return True
            time.sleep(0.25)
        return not cls.pid_is_running(pid)

    def stop(self) -> None:
        pid = self.pid()
        if pid is None or not self.pid_is_running(pid):
            self.config.pidfile.unlink(missing_ok=True)
            self.config.monitor.unlink(missing_ok=True)
            return

        log(f"stopping {self.config.name}")
        self.send_monitor_command("system_powerdown")

        if not self.wait_for_process_exit(pid, 30):
            print(f"{self.config.name} did not shut down gracefully; sending SIGTERM")
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass

        if not self.wait_for_process_exit(pid, 10):
            print(f"{self.config.name} still running; sending SIGKILL")
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
            self.wait_for_process_exit(pid, 5)

        self.config.pidfile.unlink(missing_ok=True)
        self.config.monitor.unlink(missing_ok=True)

    def wait_for_ssh(self, *, user: str | None = None, description: str) -> None:
        self.ssh_as(user or self.config.ssh_user).wait_until_available(description)

    def run(
        self,
        command: Sequence[str],
        *,
        user: str | None = None,
        check: bool = True,
        capture_output: bool = False,
        input_text: str | None = None,
        stdin: BinaryIO | TextIO | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.ssh_as(user or self.config.ssh_user).run(
            command,
            check=check,
            capture_output=capture_output,
            input_text=input_text,
            stdin=stdin,
        )

    def interactive_ssh(self, *, user: str | None = None) -> None:
        self.ssh_as(user or self.config.ssh_user).interactive()


@dataclass(frozen=True, slots=True)
class TestNetwork:
    socket_path: Path
    sut_mac: str
    sut_cidr: str
    fixture_ip: str
    fixture_cidr: str
    network_cidr: str
    printer_port: int

    def qemu_args(self, role: str, mac: str) -> list[str]:
        if role == "server":
            netdev = (
                "stream,id=testnet,server=on,addr.type=unix,"
                f"addr.path={self.socket_path}"
            )
        elif role == "client":
            netdev = (
                "stream,id=testnet,server=off,addr.type=unix,"
                f"addr.path={self.socket_path},reconnect-ms=5000"
            )
        else:
            raise ValueError(f"unknown testnet role: {role}")

        return [
            "-netdev",
            netdev,
            "-device",
            f"virtio-net-pci,netdev=testnet,mac={mac}",
        ]

    def cleanup_server_socket(self) -> None:
        self.socket_path.unlink(missing_ok=True)

    def interface_for_mac(self, ssh: SSHClient, mac: str) -> str:
        result = ssh.run(["ip", "-o", "link", "show"], capture_output=True)
        wanted = mac.casefold()
        for line in result.stdout.splitlines():
            match = _LINK_RE.search(line)
            if match and match.group("mac").casefold() == wanted:
                return match.group("name")
        die(f"could not find SUT interface with MAC {mac}")

    def verify_tcp_port(self, ssh: SSHClient, host: str, port: int) -> None:
        code = (
            "import socket; "
            f"s=socket.create_connection(({host!r}, {port}), 5); "
            "s.close()"
        )
        result = ssh.run(
            ["python", "-c", code],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            die(f"SUT cannot reach {host}:{port} over the private test network")

    def configure_sut(self, ssh: SSHClient) -> None:
        log("configuring SUT private test network")
        interface = self.interface_for_mac(ssh, self.sut_mac)

        ssh.run(
            [
                "sudo",
                "sed",
                "-i",
                "/^# BEGIN PHS VM TEST NETWORK$/,/^# END PHS VM TEST NETWORK$/d",
                "/etc/dhcpcd.conf",
            ]
        )

        config = (
            "\n# BEGIN PHS VM TEST NETWORK\n"
            f"interface {interface}\n"
            f"static ip_address={self.sut_cidr}\n"
            "nogateway\n"
            "# END PHS VM TEST NETWORK\n"
        )
        ssh.run(
            ["sudo", "tee", "-a", "/etc/dhcpcd.conf"],
            input_text=config,
            capture_output=True,
        )

        ssh.run(["sudo", "ip", "link", "set", "dev", interface, "up"])
        ssh.run(["sudo", "ip", "-4", "address", "flush", "dev", interface])
        ssh.run(["sudo", "ip", "address", "add", self.sut_cidr, "dev", interface])

        self.verify_tcp_port(ssh, self.fixture_ip, 2049)
        self.verify_tcp_port(ssh, self.fixture_ip, self.printer_port)
        print(f"SUT private interface: {interface} = {self.sut_cidr}")
