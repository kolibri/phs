from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import die, ensure_directories, log
from .archiso import ArchIso, JsonFile
from .fixture import FixtureBase
from .image import CloudInitSeed, DiskImage
from .source import SourceStager
from .vm import VM, TestNetwork, VMConfig


def create_environment() -> VMEnvironment:
    environment_dir = Path(__file__).resolve().parents[1]
    iso_dir = environment_dir / "iso"
    cache_dir = environment_dir / "cache"
    state_dir = environment_dir / "state"
    ovmf_code = Path(
        os.environ.get("PHS_VM_OVMF_CODE", "/usr/share/edk2/x64/OVMF_CODE.4m.fd")
    )
    ovmf_vars_template = Path(
        os.environ.get("PHS_VM_OVMF_VARS", "/usr/share/edk2/x64/OVMF_VARS.4m.fd")
    )
    ssh_timeout = float(os.environ.get("PHS_VM_SSH_TIMEOUT", "300"))
    sut_user = os.environ.get("PHS_VM_SUT_USER", "ko")
    sut_testnet_mac = "52:54:00:00:10:02"
    fixture_testnet_ip = "192.168.76.2"
    printer_port = 8000

    arch_iso = ArchIso(
        url="https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso",
        sha256_url="https://geo.mirror.pkgbuild.com/iso/latest/sha256sums.txt",
        path=iso_dir / "archlinux-x86_64.iso",
        metadata=JsonFile(iso_dir / "archlinux-x86_64.iso.json"),
        environment_directories=(iso_dir, cache_dir, state_dir),
    )
    cloud_init = CloudInitSeed(environment_dir / "cloud-init")
    network = TestNetwork(
        socket_path=state_dir / "testnet.sock",
        sut_mac=sut_testnet_mac,
        sut_cidr="192.168.76.10/24",
        fixture_ip=fixture_testnet_ip,
        fixture_cidr=f"{fixture_testnet_ip}/24",
        network_cidr="192.168.76.0/24",
        printer_port=printer_port,
    )

    sut = VM(
        VMConfig(
            name="phs-sut-test",
            disk=state_dir / "sut.qcow2",
            ovmf_code=ovmf_code,
            ovmf_vars=state_dir / "sut-OVMF_VARS.4m.fd",
            ovmf_vars_template=ovmf_vars_template,
            monitor=state_dir / "sut-monitor.sock",
            pidfile=state_dir / "sut.pid",
            ssh_port=int(os.environ.get("PHS_VM_SUT_SSH_PORT", "2222")),
            ssh_timeout=ssh_timeout,
            cpus=int(os.environ.get("PHS_VM_SUT_CPUS", "4")),
            memory_mib=int(os.environ.get("PHS_VM_SUT_MEMORY", "2048")),
            wan_mac="52:54:00:00:10:01",
            testnet_mac=sut_testnet_mac,
            serial="phs-sut-test",
            has_graphics=True,
            testnet_role="client",
            ssh_user=sut_user,
        ),
        network,
    )

    fixture = VM(
        VMConfig(
            name="phs-fixture-test",
            disk=state_dir / "fixture.qcow2",
            ovmf_code=ovmf_code,
            ovmf_vars=state_dir / "fixture-OVMF_VARS.4m.fd",
            ovmf_vars_template=ovmf_vars_template,
            monitor=state_dir / "fixture-monitor.sock",
            pidfile=state_dir / "fixture.pid",
            ssh_port=int(os.environ.get("PHS_VM_FIXTURE_SSH_PORT", "2223")),
            ssh_timeout=ssh_timeout,
            cpus=int(os.environ.get("PHS_VM_FIXTURE_CPUS", "2")),
            memory_mib=int(os.environ.get("PHS_VM_FIXTURE_MEMORY", "512")),
            wan_mac="52:54:00:00:20:01",
            testnet_mac="52:54:00:00:20:02",
            serial="phs-fixture-test",
            has_graphics=False,
            testnet_role="server",
            ssh_user="root",
        ),
        network,
    )

    fixture_base = FixtureBase(
        arch_iso=arch_iso,
        disk=DiskImage(cache_dir / "fixture-base.qcow2"),
        ovmf_vars=cache_dir / "fixture-base-OVMF_VARS.4m.fd",
        metadata=JsonFile(cache_dir / "fixture-base.json"),
        provision=environment_dir / "provision" / "fixture.sh",
        cloud_init=cloud_init,
        managed_vms=(sut, fixture),
        fixture_template=fixture,
        cache_dir=cache_dir,
        disk_size=os.environ.get("PHS_VM_FIXTURE_DISK_SIZE", "8G"),
    )

    sut_home = os.environ.get("PHS_VM_SUT_HOME", f"/home/{sut_user}")
    source_stager = SourceStager(
        project_root=environment_dir.parents[2],
        destination=os.environ.get(
            "PHS_VM_SUT_PROJECT_DIR", f"{sut_home}/projects/phs"
        ),
        sut=sut,
    )

    return VMEnvironment(
        arch_iso=arch_iso,
        cloud_init=cloud_init,
        network=network,
        sut=sut,
        fixture=fixture,
        fixture_base=fixture_base,
        source_stager=source_stager,
        state_dir=state_dir,
        cache_dir=cache_dir,
        ovmf_vars_template=ovmf_vars_template,
        sut_disk_size=os.environ.get("PHS_VM_SUT_DISK_SIZE", "64G"),
        printer_uri=f"ipp://{fixture_testnet_ip}:{printer_port}/ipp/print",
    )


@dataclass(frozen=True, slots=True)
class VMEnvironment:
    arch_iso: ArchIso
    cloud_init: CloudInitSeed
    network: TestNetwork
    sut: VM
    fixture: VM
    fixture_base: FixtureBase
    source_stager: SourceStager
    state_dir: Path
    cache_dir: Path
    ovmf_vars_template: Path
    sut_disk_size: str

    printer_uri: str

    def assert_all_stopped(self) -> None:
        self.sut.assert_stopped()
        self.fixture.assert_stopped()

    def stop_sut(self) -> None:
        self.sut.stop()

    def stop_fixture(self) -> None:
        self.fixture.stop()
        self.network.cleanup_server_socket()

    def stop_all(self) -> None:
        self.stop_sut()
        self.stop_fixture()

    def clean_state(self) -> None:
        self.assert_all_stopped()
        log("cleaning VM run state")
        shutil.rmtree(self.state_dir, ignore_errors=True)
        self.state_dir.mkdir(parents=True)

    def clean_all(self) -> None:
        self.stop_all()
        self.clean_state()
        log("cleaning VM cache")
        for path in (
            self.fixture_base.disk.path,
            self.fixture_base.ovmf_vars,
            self.fixture_base.metadata.path,
        ):
            path.unlink(missing_ok=True)
        shutil.rmtree(self.cache_dir / ".fixture-build", ignore_errors=True)
        print(f"Arch ISO retained: {self.arch_iso.path}")

    def invalidate_fixture_state(self) -> None:
        self.fixture.disk.unlink(missing_ok=True)
        self.fixture.ovmf_vars.unlink(missing_ok=True)

    def build_fixture_base(self) -> None:
        if self.fixture_base.is_current():
            print(f"Fixture base is current: {self.fixture_base.disk.path}")
            return

        self.stop_all()
        self.invalidate_fixture_state()
        self.fixture_base.build()

    def rebuild_fixture_base(self) -> None:
        self.stop_all()
        self.invalidate_fixture_state()
        self.fixture_base.rebuild()

    def prepare(self) -> None:
        self.sut.check_requirements(installer=True)
        ensure_directories(*self.arch_iso.environment_directories)
        self.assert_all_stopped()
        self.arch_iso.ensure_current()

        if not self.fixture_base.is_current():
            self.fixture_base.build(force=True, ensure_iso=False)

        self.clean_state()

        log("creating fresh SUT disk")
        DiskImage(self.sut.disk).create(self.sut_disk_size)
        shutil.copy2(self.ovmf_vars_template, self.sut.ovmf_vars)

        log("creating fresh fixture overlay")
        DiskImage(self.fixture.disk).create_overlay(self.fixture_base.disk.path)
        shutil.copy2(self.fixture_base.ovmf_vars, self.fixture.ovmf_vars)

        self.cloud_init.create(self.state_dir, instance_id="phs-sut-test")
        print("VM environment prepared")

    def boot_fixture(self) -> None:
        self.fixture.boot()

    def boot_sut_installer(self) -> None:
        self.sut.boot(
            installer_iso=self.arch_iso.path,
            cloud_init_iso=self.state_dir / "cloud-init.iso",
        )

    def boot_sut(self) -> None:
        self.sut.boot()

    def boot_sut_gui(self) -> None:
        self.sut.boot(gui=True)

    def wait_fixture(self) -> None:
        self.fixture.wait_for_ssh(description="fixture")

        for service in ("nfs-server.service", "phs-test-printer.service"):
            log(f"waiting for fixture {service}")
            deadline = time.monotonic() + self.fixture.config.ssh_timeout
            while time.monotonic() < deadline:
                result = self.fixture.run(
                    ["systemctl", "is-active", "--quiet", service],
                    check=False,
                    capture_output=True,
                )
                if result.returncode == 0:
                    print(f"{service} is active")
                    break
                time.sleep(0.25)
            else:
                die(f"fixture service did not become active: {service}")

    def wait_sut_root(self) -> None:
        self.sut.wait_for_ssh(user="root", description="SUT installer")

    def wait_sut_user(self) -> None:
        self.sut.wait_for_ssh(description="SUT")

    def configure_sut_testnet(self) -> None:
        self.network.configure_sut(self.sut.ssh)

    def stage_source(self) -> None:
        self.source_stager.stage()

    @staticmethod
    def command_result(completed: subprocess.CompletedProcess[str]) -> None:
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)

    def exec_sut(self, command: Sequence[str]) -> None:
        if not command:
            die("exec-sut requires a command")
        self.command_result(self.sut.run(command, check=False))

    def exec_fixture(self, command: Sequence[str]) -> None:
        if not command:
            die("exec-fixture requires a command")
        self.command_result(self.fixture.run(command, check=False))

    def status(self) -> None:
        print(f"SUT: {'running' if self.sut.is_running() else 'stopped'}")
        print(f"Fixture: {'running' if self.fixture.is_running() else 'stopped'}")
        print(f"Arch ISO: {'present' if self.arch_iso.path.is_file() else 'missing'}")
        current = (
            self.arch_iso.path.is_file()
            and self.arch_iso.metadata.path.is_file()
            and self.fixture_base.is_current()
        )
        print(f"Fixture base: {'current' if current else 'missing/stale'}")
        print(f"Printer URI: {self.printer_uri}")
