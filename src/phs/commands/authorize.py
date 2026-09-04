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
from phs.tasks.sshkey_ensure import SshkeyEnsure


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
) -> bool:
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

    return completed.returncode == 0


def _inventory_hosts(
        context: AppContext,
        target_host: str | None = None,
) -> list[str]:
    hosts = sorted(
        path.stem
        for path in context.settings.config_dir.glob("*.yaml")
        if path.name != "all.yaml"
    )

    if target_host is None:
        return hosts

    if target_host not in hosts:
        raise ValueError(f"Unknown target host: {target_host}")

    return [target_host]


def authorize(
        *,
        host: str = "local",
        target_host: str | None = None,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    source = ExecutionFactory.create(context, host=host, dry_run=False)

    private_key = Path(source.data.homedir) / ".ssh" / "id_ed25519"
    public_key_path = Path(f"{private_key}.pub")

    Executor.execute([
        SshkeyEnsure(private_key),
    ], source.target)

    public_key = source.target.filesystem.read_text(public_key_path)
    source_hostname = source.data.hostname

    context.output.info(f"Authorizing host '{source_hostname}' to the other hosts.")

    for inventory_host in _inventory_hosts(context, target_host):
        destination = context.inventory.load(inventory_host)

        if destination.hostname == source_hostname:
            continue

        context.output.info(f"Authorizing host '{source_hostname}' to {destination.hostname}.")

        if _can_connect(source.target, private_key, destination):
            context.output.info(f"Already authorized on {destination.hostname}.")
            continue

        context.output.warning(f"Authentication required for {destination.hostname}.")

        if not _install_public_key(public_key, destination):
            context.output.warning(f"Could not authorize {destination.hostname}; skipping host.")
            continue

        if not _can_connect(source.target, private_key, destination):
            context.output.warning(f"Authorization of {destination.hostname} could not be verified; skipping host.")
            continue

        context.output.success(f"Successfully authorized on {destination.hostname}.")
