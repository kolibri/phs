from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from . import ensure_directories, log, require_file
from .archiso import ArchIso, JsonFile, Sha256
from .image import CloudInitSeed, DiskImage
from .ssh import SSHClient
from .vm import VM, TestNetwork

FIXTURE_BASE_CACHE_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class FixtureBase:
    arch_iso: ArchIso
    disk: DiskImage
    ovmf_vars: Path
    metadata: JsonFile
    provision: Path
    cloud_init: CloudInitSeed
    managed_vms: tuple[VM, ...]
    fixture_template: VM
    cache_dir: Path
    disk_size: str

    def definition(self) -> dict[str, object]:
        require_file(self.provision)

        config = self.fixture_template.config
        network = self.fixture_template.network

        return {
            "cache_version": FIXTURE_BASE_CACHE_VERSION,
            "archiso_sha256": str(self.arch_iso.sha256()),
            "provision_sha256": str(Sha256.from_file(self.provision)),
            "ssh_public_key_sha256": str(Sha256.from_text(SSHClient.public_key())),
            "ovmf_code_sha256": str(Sha256.from_file(config.ovmf_code)),
            "ovmf_vars_template_sha256": str(
                Sha256.from_file(config.ovmf_vars_template)
            ),
            "disk_size": self.disk_size,
            "wan_mac": config.wan_mac,
            "testnet_mac": config.testnet_mac,
            "testnet_cidr": network.fixture_cidr,
            "network_cidr": network.network_cidr,
            "printer_port": network.printer_port,
        }

    def is_current(self) -> bool:
        if not (
            self.disk.path.is_file()
            and self.ovmf_vars.is_file()
            and self.metadata.path.is_file()
        ):
            return False
        return self.metadata.read() == self.definition()

    def assert_all_stopped(self) -> None:
        for vm in self.managed_vms:
            vm.assert_stopped()

    def build(self, *, force: bool = False, ensure_iso: bool = True) -> None:
        ensure_directories(*self.arch_iso.environment_directories)
        self.assert_all_stopped()
        if ensure_iso:
            self.arch_iso.ensure_current()
        require_file(self.provision)

        if self.is_current() and not force:
            print(f"Fixture base is current: {self.disk.path}")
            return

        build_dir = self.cache_dir / ".fixture-build"
        shutil.rmtree(build_dir, ignore_errors=True)
        build_dir.mkdir(parents=True)

        builder_network = replace(
            self.fixture_template.network,
            socket_path=build_dir / "testnet.sock",
        )
        builder_config = replace(
            self.fixture_template.config,
            name="phs-fixture-builder",
            disk=build_dir / "fixture-base.qcow2",
            ovmf_vars=build_dir / "OVMF_VARS.4m.fd",
            monitor=build_dir / "monitor.sock",
            pidfile=build_dir / "qemu.pid",
            serial="phs-fixture-base",
            has_graphics=False,
            testnet_role="server",
            ssh_user="root",
        )
        builder = VM(builder_config, builder_network)

        log("building reusable network fixture base")
        DiskImage(builder.disk).create(self.disk_size)
        shutil.copy2(builder.config.ovmf_vars_template, builder.ovmf_vars)
        cloud_init_iso = self.cloud_init.create(
            build_dir,
            instance_id="phs-fixture-builder",
        )

        builder.boot(
            installer_iso=self.arch_iso.path,
            cloud_init_iso=cloud_init_iso,
        )

        try:
            builder.wait_for_ssh(
                user="root",
                description="fixture Arch installer",
            )
            network: TestNetwork = builder.network
            builder.run(
                [
                    "bash",
                    "-s",
                    "--",
                    "/dev/nvme0n1",
                    "phs-fixture",
                    builder.config.wan_mac,
                    builder.config.testnet_mac,
                    network.fixture_cidr,
                    network.network_cidr,
                    str(network.printer_port),
                    SSHClient.public_key(),
                ],
                user="root",
                input_text=self.provision.read_text(encoding="utf-8"),
            )
        finally:
            builder.stop()

        self.disk.path.unlink(missing_ok=True)
        self.ovmf_vars.unlink(missing_ok=True)
        shutil.move(builder.disk, self.disk.path)
        shutil.move(builder.ovmf_vars, self.ovmf_vars)
        self.metadata.write(self.definition())
        shutil.rmtree(build_dir, ignore_errors=True)
        print(f"Fixture base created: {self.disk.path}")

    def rebuild(self) -> None:
        for path in (
            self.disk.path,
            self.ovmf_vars,
            self.metadata.path,
        ):
            path.unlink(missing_ok=True)

        self.build(force=True)
