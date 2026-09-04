import getpass
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.ssh import SSHTarget


def install(
        host: str,
        *,
        userpassword: str | None = None,
        force: bool = False,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    data = context.inventory.load(host)
    if not force:
        context.output.warning(f"This will ERASE the disk {data.hdd} on {data.hostname} ({data.ip}).")
        answer = context.output.prompt("Continue? [y/N] ").strip().lower()
        if answer != "yes":
            context.output.info("Installation aborted.")
            return

    if userpassword is None:
        userpassword = getpass.getpass(f"Password for {data.username}: ")
        confirmation = getpass.getpass("Confirm password: ")

        if userpassword != confirmation:
            context.output.error("Passwords do not match.")
            return

    install_script = context.builtin_templates.render(
        'scripts/install_arch.sh.j2',
        hdd=data.hdd,
        host_pubkey=Path(context.settings.sshkey).read_text(),
        hostname=data.hostname,
        username=data.username,
        groupname=data.groupname,
        user_password=userpassword
    )

    context.output.info(f"Starting installation of {data.hostname} at {data.ip}.")

    target = SSHTarget(
        host=data.ip,
        user='root',
        port=data.ssh_port,
    )
    context.ssh.run_script(target, install_script)

    context.output.success(f"Finished installation of {data.hostname} at {data.ip}.")
    context.output.success("Next step: Reboot, and run the 'init', 'authorize' and 'setup' command.")
