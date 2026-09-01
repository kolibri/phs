import re
from dataclasses import dataclass
from pathlib import Path
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
        target.filesystem.write_text(
            self.path,
            self.content,
            root=self.root,
        )



import re
from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
@dataclass(frozen=True, slots=True)
class FileEnsureLine:
    path: Path
    line: str
    match: str
    root: bool

    def execute(self, target: TargetContext) -> None:
        content = target.filesystem.read_text(
            self.path,
            root=self.root,
        )

        pattern = re.compile(
            self.match,
            re.MULTILINE,
        )

        if pattern.search(content):
            new_content = pattern.sub(
                self.line,
                content,
                count=1,
            )
        else:
            new_content = content

            if new_content and not new_content.endswith("\n"):
                new_content += "\n"

            new_content += f"{self.line}\n"

        if new_content == content:
            return

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
    ) -> Task:
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