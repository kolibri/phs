from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators

from phs.cli import AppContext
from phs.ssh import SSHTarget


def install(
        host: str,
        *,
        userpassword: str,
        context: Annotated[AppContext, Parameter(parse=False)],
):
    data = context.inventory.load(host)
    install_script = context.builtin_templates.render(
        'scripts/install_arch.sh.j2',
        hdd=data.hdd,
        host_pubkey=Path(context.settings.sshkey).read_text(),
        hostname=data.hostname,
        username=data.username,
        groupname=data.groupname,
        user_password=userpassword
    )
    # print(install_script)

    target = SSHTarget(
        host=data.ip,
        user='root',
        port=data.ssh_port,
    )
    context.ssh.run_script(target, install_script)
