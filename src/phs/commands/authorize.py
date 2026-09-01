import shlex
import subprocess
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionFactory
from phs.executor import Executor
from phs.inventory import HostData
from phs.target.context import TargetContext
from phs.tasks.sshkey import Sshkey


def _can_connect(
    source: TargetContext,
    private_key: Path,
    destination: HostData,
) -> bool:
    result = source.runner.run(
        [
            "ssh",
            "-i",
            str(private_key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=5",
            "-p",
            str(destination.ssh_port),
            f"{destination.username}@{destination.ip}",
            "true",
        ],
        capture_output=True,
        check=False,
    )

    return result.returncode == 0


def _install_public_key(
    public_key: str,
    destination: HostData,
) -> None:
    quoted_key = shlex.quote(public_key.strip())

    script = f"""
set -eu

umask 077

mkdir -p "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"

if ! grep -qxF -- {quoted_key} "$HOME/.ssh/authorized_keys"; then
    printf '%s\\n' {quoted_key} >> "$HOME/.ssh/authorized_keys"
fi

chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/authorized_keys"
"""

    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=10",
            "-p",
            str(destination.ssh_port),
            f"{destination.username}@{destination.ip}",
            "sh",
            "-s",
        ],
        input=script,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"Failed to authorize key on {destination.hostname}"
        )


def _inventory_hosts(context: AppContext) -> list[str]:
    return sorted(
        path.stem
        for path in context.settings.config_dir.glob("*.yaml")
        if path.name != "all.yaml"
    )


def authorize(
    *,
    host: str = "local",
    context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    source = ExecutionFactory.create(
        context,
        host=host,
        dry_run=False,
    )

    private_key = (
        Path(source.data.homedir)
        / ".ssh"
        / "id_ed25519"
    )

    public_key_path = Path(f"{private_key}.pub")

    Executor.execute(
        [
            Sshkey.ensure(private_key),
        ],
        source.target,
    )

    public_key = source.target.filesystem.read_text(
        public_key_path,
    )

    source_hostname = source.data.hostname

    for inventory_host in _inventory_hosts(context):
        destination = context.inventory.load(inventory_host)

        if destination.hostname == source_hostname:
            continue

        print(
            f"Authorize {source_hostname} -> "
            f"{destination.hostname}"
        )

        if _can_connect(
            source.target,
            private_key,
            destination,
        ):
            print("  already authorized")
            continue

        print("  authentication required")

        _install_public_key(
            public_key,
            destination,
        )

        if not _can_connect(
            source.target,
            private_key,
            destination,
        ):
            raise RuntimeError(
                f"Authorization succeeded, but "
                f"{source_hostname} cannot connect to "
                f"{destination.hostname}"
            )

        print("  authorized")