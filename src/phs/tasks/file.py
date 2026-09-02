import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class FileWrite:
    path: Path
    content: str
    root: bool

    def execute(self, target: TargetContext) -> None:
        target.output.info(f'Ensuring file {str(self.path)}')

        target.filesystem.write_text(
            self.path,
            self.content,
            root=self.root,
        )


@final
@dataclass(frozen=True, slots=True)
class FileEnsureLine:
    path: Path
    line: str
    match: str
    root: bool

    def execute(self, target: TargetContext) -> None:
        target.output.info(f'Ensuring line for {self.match} in {str(self.path)}')

        content = target.filesystem.read_text(
            self.path,
            root=self.root,
        )

        pattern = re.compile(self.match)

        lines = content.splitlines(keepends=True)

        for index, current_line in enumerate(lines):
            line = current_line.rstrip("\r\n")

            if not pattern.search(line):
                continue

            line_ending = (
                "\r\n"
                if current_line.endswith("\r\n")
                else "\n"
                if current_line.endswith("\n")
                else ""
            )

            new_line = f"{self.line}{line_ending}"

            if current_line == new_line:
                return

            lines[index] = new_line

            target.filesystem.write_text(
                self.path,
                "".join(lines),
                root=self.root,
            )
            return

        new_content = content

        if new_content and not new_content.endswith("\n"):
            new_content += "\n"

        new_content += f"{self.line}\n"

        target.filesystem.write_text(
            self.path,
            new_content,
            root=self.root,
        )


@final
class File:
    @staticmethod
    def write(
        path: Path,
        content: str,
        *,
        root: bool = False,
        as_given: bool = False,
    ) -> Task:
        if not as_given:
            content = dedent(content).strip() + "\n"

        return FileWrite(
            path=path,
            content=content,
            root=root,
        )

    @staticmethod
    def ensure_line(
        path: Path,
        line: str,
        *,
        match: str | None = None,
        root: bool = False,
    ) -> Task:
        return FileEnsureLine(
            path=path,
            line=line,
            match=match or rf"^{re.escape(line)}$",
            root=root,
        )