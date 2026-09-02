from dataclasses import dataclass
from mimetypes import guess_file_type
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class FileAssociationEnsure:
    associations: tuple[tuple[str, str], ...]

    @staticmethod
    def _mime_type(extension: str) -> str:
        extension = extension.removeprefix(".")
        mime_type, _ = guess_file_type(f"file.{extension}")

        if mime_type is None:
            raise ValueError(
                f"Could not determine MIME type for extension '{extension}'"
            )

        return mime_type

    @staticmethod
    def _desktop_file(
            target: TargetContext,
            application: str,
    ) -> str:
        result = target.runner.run(
            [
                "mimeo",
                "--app2desk",
                application,
            ],
            capture_output=True,
        )

        desktop_files = [
            line.strip()
            for line in (result.stdout or "").splitlines()
            if line.strip().endswith(".desktop")
        ]

        if not desktop_files:
            raise RuntimeError(
                f"Could not find desktop file for application '{application}'"
            )

        return desktop_files[0]

    def execute(self, target: TargetContext) -> None:
        for extension, application in self.associations:
            mime_type = self._mime_type(extension)
            desktop_file = self._desktop_file(target, application)

            target.output.info(
                f"Ensuring .{extension.removeprefix('.')} opens with {application}"
            )
            target.runner.run([
                "mimeo",
                "--prefer",
                mime_type,
                desktop_file,
            ])


@final
class FileAssociation:
    @staticmethod
    def ensure(associations: dict[str, str]) -> Task:
        return FileAssociationEnsure(
            associations=tuple(associations.items()),
        )
