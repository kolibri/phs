from typing import Annotated

from cyclopts import App, Parameter

from phs.config_repository import ConfigRepository
from phs.context import AppContext
from phs.execution import Execution, ExecutionFactory, ExecutionOptions
from phs.executor import Executor
from phs.inventory.editor import InventoryChange, InventoryEditor
from phs.tasks.aur_install import AurInstall
from phs.tasks.file_association_ensure import FileAssociationEnsure
from phs.tasks.fnt_install import FntInstall
from phs.tasks.pacman_install import PacmanInstall
from phs.tasks.service_enable import ServiceEnable
from phs.tasks.task import Task

add = App(name="add")


def _execute_add(
        *,
        description: str,
        change: InventoryChange,
        commit_message: str,
        task: Task,
        execution: Execution,
        options: ExecutionOptions,
        context: AppContext,
        repository: ConfigRepository,
) -> None:
    if options.dry_run:
        context.output.info(f"Would ensure {description}.")
        change.show(context.output)
        if change.changed:
            context.output.info(f'Would create configuration commit: "{commit_message}"')
        return

    Executor.execute([task], execution.target)
    change.apply()

    if change.changed:
        repository.commit([change.path], commit_message)
        context.output.success(
            f"Added {description} to {execution.data.hostname}."
        )
    else:
        context.output.info(
            f"{description.capitalize()} is already configured."
        )


def _execution(
        options: ExecutionOptions,
        context: AppContext,
) -> tuple[Execution, InventoryEditor, ConfigRepository]:
    repository = ConfigRepository(
        context.settings.config_dir,
        context.output,
    )
    repository.require_clean()

    execution = ExecutionFactory.create(
        context,
        host=options.host,
        dry_run=options.dry_run,
    )
    return (
        execution,
        InventoryEditor(context.settings.config_dir),
        repository,
    )


def pkg(
        package: str,
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution, editor, repository = _execution(options, context)
    change = editor.add_package(execution.data.hostname, package)

    _execute_add(
        description=f"pacman package {package}",
        change=change,
        commit_message=f"Add package {package} to {execution.data.hostname}",
        task=PacmanInstall((package,)),
        execution=execution,
        options=options,
        context=context,
        repository=repository,
    )


def aur(
        package: str,
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution, editor, repository = _execution(options, context)
    change = editor.add_aur_package(execution.data.hostname, package)

    _execute_add(
        description=f"AUR package {package}",
        change=change,
        commit_message=f"Add AUR package {package} to {execution.data.hostname}",
        task=AurInstall((package,), context.builtin_templates),
        execution=execution,
        options=options,
        context=context,
        repository=repository,
    )


def font(
        name: str,
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution, editor, repository = _execution(options, context)
    change = editor.add_font(execution.data.hostname, name)

    _execute_add(
        description=f"font {name}",
        change=change,
        commit_message=f"Add font {name} to {execution.data.hostname}",
        task=FntInstall((name,)),
        execution=execution,
        options=options,
        context=context,
        repository=repository,
    )


def service(
        name: str,
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution, editor, repository = _execution(options, context)
    change = editor.add_service(execution.data.hostname, name)

    _execute_add(
        description=f"service {name}",
        change=change,
        commit_message=f"Add service {name} to {execution.data.hostname}",
        task=ServiceEnable((name,)),
        execution=execution,
        options=options,
        context=context,
        repository=repository,
    )


def app_for(
        extension: str,
        application: str,
        *,
        options: ExecutionOptions = ExecutionOptions(),
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    execution, editor, repository = _execution(options, context)
    extension = extension.removeprefix(".")
    change = editor.set_file_association(
        execution.data.hostname,
        extension,
        application,
    )

    _execute_add(
        description=f"application {application} for .{extension}",
        change=change,
        commit_message=(
            f"Set .{extension} application to {application} "
            f"on {execution.data.hostname}"
        ),
        task=FileAssociationEnsure(((extension, application),)),
        execution=execution,
        options=options,
        context=context,
        repository=repository,
    )


add.command(pkg, name="pkg")
add.command(aur, name="aur")
add.command(font, name="font")
add.command(service, name="service")
add.command(app_for, name="app-for")
