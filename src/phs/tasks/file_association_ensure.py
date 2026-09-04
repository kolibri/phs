from dataclasses import dataclass
from mimetypes import guess_file_type
from typing import final

from phs.target.context import TargetContext


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
    def _desktop_files(output: str | None) -> list[str]:
        return [
            line.strip()
            for line in (output or "").splitlines()
            if line.strip().endswith(".desktop")
        ]

    @classmethod
    def _desktop_file(
        cls,
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

        desktop_files = cls._desktop_files(result.stdout)

        if not desktop_files:
            raise RuntimeError(
                f"Could not find desktop file for application '{application}'"
            )

        return desktop_files[0]

    @classmethod
    def _current_desktop_file(
        cls,
        target: TargetContext,
        mime_type: str,
    ) -> str | None:
        result = target.runner.run(
            [
                "mimeo",
                "--mime2desk",
                mime_type,
            ],
            capture_output=True,
            check=False,
        )

        desktop_files = cls._desktop_files(result.stdout)
        return desktop_files[0] if desktop_files else None

    def execute(self, target: TargetContext) -> None:
        for extension, application in self.associations:
            mime_type = self._mime_type(extension)
            desktop_file = self._desktop_file(target, application)

            if self._current_desktop_file(target, mime_type) == desktop_file:
                continue

            target.output.info(
                f"Ensuring .{extension.removeprefix('.')} opens with {application}"
            )
            target.runner.run([
                "mimeo",
                "--prefer",
                mime_type,
                desktop_file,
            ])
