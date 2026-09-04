import re
from dataclasses import dataclass
from pathlib import Path
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class EnsureLine:
    path: Path
    line: str
    match: str = ""
    root: bool = False

    def __post_init__(self) -> None:
        if not self.match:
            object.__setattr__(self, "match", rf"^{re.escape(self.line)}$")

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Ensuring line for {self.match} in {self.path}")

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
