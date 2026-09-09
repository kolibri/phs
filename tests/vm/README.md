# PHS VM tests

The repository-root `test.sh` is the public test entrypoint.

The VM area has three distinct responsibilities:

```text
tests/vm/
├── tests/          pytest assertions: what do we verify?
├── hostconfig/     PHS inventory: what configuration do we apply?
└── environment/    QEMU environment: where/how do we run it?
```

## Layout

```text
tests/
├── unit/                          # default pytest suite
└── vm/
    ├── tests/
    │   ├── conftest.py
    │   ├── test_install.py
    │   ├── test_setup.py
    │   ├── test_nfs.py
    │   ├── test_printer.py
    │   ├── test_desktop.py
    │   └── test_idempotency.py
    │
    ├── hostconfig/
    │   ├── all.yaml
    │   ├── phs-test.yaml
    │   └── files/
    │
    └── environment/
        ├── manage.py                    # environment CLI only
        ├── lib/
        │   ├── __init__.py              # tiny shared helpers
        │   ├── environment.py           # VMEnvironment + composition root
        │   ├── vm.py                    # VM, VMConfig, TestNetwork
        │   ├── ssh.py                   # SSHClient
        │   ├── image.py                 # DiskImage, CloudInitSeed
        │   ├── archiso.py               # ArchIso, Sha256, JsonFile
        │   ├── fixture.py               # FixtureBase
        │   └── source.py                # SourceStager
        ├── cloud-init/
        ├── provision/
        │   └── fixture.sh
        ├── iso/                         # ignored
        ├── cache/                       # ignored
        └── state/                       # ignored
```

`manage.py` only parses CLI actions and dispatches to `VMEnvironment`.
The actual behavior lives in the classes under `environment/lib`.

## Test suites

`pyproject.toml` uses:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
```

So:

```bash
./test.sh
```

runs Ruff and the unit suite only, while:

```bash
./test.sh vm
```

runs the VM workflow and explicitly executes:

```bash
uv run pytest tests/vm/tests
```

No pytest markers are needed. The directory is the suite.

## VM topology

```text
host
├── 127.0.0.1:2222 -> SUT SSH
└── 127.0.0.1:2223 -> fixture SSH

private QEMU stream network: 192.168.76.0/24
├── SUT      192.168.76.10
└── fixture  192.168.76.2
    ├── NFS          :2049
    └── IPP printer  :8000
```

The fixture VM provides both external network dependencies:

- `/srv/phs-test` exported over NFS
- an IPP Everywhere printer from `ippeveprinter`

The printer URI is:

```text
ipp://192.168.76.2:8000/ipp/print
```

Received print jobs are retained under `/var/spool/phs-test-printer`, so the
printer VM test proves that a real CUPS job crossed the private network.

## Arch ISO

Both VMs use the same ISO. The full ISO is downloaded only from:

```text
https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso
```

Before `prepare`, `ArchIso` fetches the small official checksum list:

```text
https://geo.mirror.pkgbuild.com/iso/latest/sha256sums.txt
```

The cached ISO is hashed locally and is only downloaded again when the
published checksum changed or the local ISO is missing/corrupt.

The fixture base is invalidated when the Arch checksum, fixture provisioning
script, SSH public key, or fixture network/printer definition changes.

## Full VM flow

```bash
./test.sh vm
```

1. Ruff + unit tests.
2. Verify/download the current Arch ISO.
3. Build the fixture base if missing/stale.
4. Create a fresh SUT disk and fixture overlay.
5. Boot the fixture and wait for SSH, NFS, and IPP services.
6. Boot the SUT from the Arch ISO.
7. Run the real `phs install` from the host working tree.
8. Boot the installed SUT and configure its private test NIC.
9. Run the real `phs init`, including its GitHub clone.
10. Overlay the current tracked + untracked/non-ignored local source while
    preserving the cloned `.git` directory.
11. Install that source inside the SUT.
12. Run `phs setup` twice.
13. Run `pytest tests/vm/tests`.
14. Reboot the SUT.
15. Run `pytest tests/vm/tests` again.

Run state is retained after success or failure for manual debugging.

## Manual inspection and debugging

```bash
./test.sh vm-gui
./test.sh vm-ssh
./test.sh vm-ssh-fixture
./test.sh vm-status
```

Cleanup current run state while retaining the ISO and fixture base:

```bash
./test.sh vm-clean
```

Rebuild the fixture base:

```bash
./test.sh vm-rebuild-fixture
```

Force a full Arch ISO redownload:

```bash
./test.sh vm-download-archiso-force
```

## Host requirements

- QEMU/KVM
- `qemu-img`
- `xorriso`
- OpenSSH client
- Git
- tar
- OVMF/edk2 firmware, by default:
    - `/usr/share/edk2/x64/OVMF_CODE.4m.fd`
    - `/usr/share/edk2/x64/OVMF_VARS.4m.fd`
- an SSH key at `~/.ssh/id_ed25519` or `~/.ssh/id_rsa`

Overrides:

```bash
PHS_VM_SSH_KEY=/path/to/key ./test.sh vm
PHS_VM_OVMF_CODE=/path/to/OVMF_CODE.fd ./test.sh vm
PHS_VM_OVMF_VARS=/path/to/OVMF_VARS.fd ./test.sh vm
```
