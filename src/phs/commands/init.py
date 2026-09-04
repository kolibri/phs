from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from phs.context import AppContext
from phs.execution import ExecutionFactory, ExecutionOptions
from phs.executor import Executor
from phs.tasks.copy_path import CopyPath
from phs.tasks.directory_create import DirectoryCreate
from phs.tasks.git_clone import GitClone
from phs.tasks.pacman_update import PacmanUpdate
from phs.tasks.sshkey_ensure import SshkeyEnsure
from phs.tasks.task import Task


def init(
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
):
    execution = ExecutionFactory.create(context, host=options.host, dry_run=options.dry_run)
    data = execution.data

    context.output.info(f"Starting initializing new host {data.hostname}.")

    tasks: list[Task] = [
        PacmanUpdate(),
        SshkeyEnsure(Path(data.homedir) / ".ssh" / "id_ed25519"),
        DirectoryCreate(Path(data.homedir) / "projects"),
        GitClone("https://github.com/kolibri/phs.git", Path(data.homedir) / "projects" / "phs"),
        CopyPath(
            Path(context.settings.config_dir),
            Path(data.homedir) / ".phs" / "hosts",
            create_dirs=True,
            exclude=(
                "test/qemu/iso",
                "test/qemu/state",
                ".idea",
                ".venv",
                "__pycache__",
            ),
        ),
    ]

    Executor.execute(
        tasks,
        execution.target,
    )

    context.output.success(f"Done initializing new host {data.hostname}.")
