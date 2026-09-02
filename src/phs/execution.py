from dataclasses import dataclass
from typing import final

from phs.context import AppContext
from phs.inventory import HostData
from phs.target.context import TargetContext
from phs.target.dryrun.dryrun_filesystem import DryRunFilesystem
from phs.target.dryrun.dryrun_runner import DryRunRunner
from phs.target.dryrun.dryrun_transfer import DryRunTransfer
from phs.target.filesystem import Filesystem, RunnerFilesystem
from phs.target.local.local_runner import LocalRunner
from phs.target.local.local_transfer import LocalTransfer
from phs.target.remote.remote_runner import RemoteRunner
from phs.target.remote.remote_transfer import RemoteTransfer
from phs.target.runner import Runner, OutputRunner
from phs.target.transfer import Transfer
from cyclopts import Parameter


@Parameter(name="*")
@dataclass(frozen=True, slots=True)
class ExecutionOptions:
    host: str = "local"
    dry_run: bool = False


@final
@dataclass(frozen=True, slots=True)
class Execution:
    data: HostData
    target: TargetContext


@final
class ExecutionFactory:
    @staticmethod
    def create(
        context: AppContext,
        *,
        host: str,
        dry_run: bool,
    ) -> Execution:
        target_host = (
            context.settings.my_hostname
            if host == "local"
            else host
        )

        data = context.inventory.load(target_host)

        runner: Runner
        transfer: Transfer

        if host == "local":
            local_runner = LocalRunner()

            runner = local_runner
            transfer = LocalTransfer(local_runner)
        else:
            remote_runner = RemoteRunner(
                data.ip,
                data.username,
                port=data.ssh_port,
            )

            runner = remote_runner
            transfer = RemoteTransfer(remote_runner)

        runner = OutputRunner(runner, context.output)
        filesystem: Filesystem = RunnerFilesystem(runner)

        if dry_run:
            target = TargetContext(
                runner=DryRunRunner(runner),
                filesystem=DryRunFilesystem(filesystem),
                transfer=DryRunTransfer(transfer),
                output = context.output
            )
        else:
            target = TargetContext(
                runner=runner,
                filesystem=filesystem,
                transfer=transfer,
                output=context.output
            )

        return Execution(
            data=data,
            target=target,
        )