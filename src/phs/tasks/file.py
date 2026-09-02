import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Literal, final

from phs.target.context import TargetContext
from phs.tasks.task import Task


type WatchAction = Literal["keep", "restore", "apply"]


def _watch_action(
        target: TargetContext,
        *,
        can_restore: bool,
        can_apply: bool,
) -> WatchAction:
    if target.watch.force:
        target.output.warning("forced change")
        if can_apply:
            return "apply"
        if can_restore:
            return "restore"

    choices: list[str] = ["[k]eep current"]
    valid: dict[str, WatchAction] = {"k": "keep"}

    if can_restore:
        choices.append("[r]estore cached")
        valid["r"] = "restore"

    if can_apply:
        choices.append("[a]pply phs")
        valid["a"] = "apply"

    prompt = f"Choose {', '.join(choices)}: "

    while True:
        answer = target.output.prompt(prompt).strip().lower()

        if answer in valid:
            return valid[answer]

        target.output.warning("Invalid choice")


@final
@dataclass(frozen=True, slots=True)
class FileWrite:
    path: Path
    content: str
    root: bool
    watched: bool

    def _write(
            self,
            target: TargetContext,
            content: str,
    ) -> None:
        target.filesystem.write_text(
            self.path,
            content,
            root=self.root,
        )

    def execute(self, target: TargetContext) -> None:
        target.output.info(f"Ensuring file {self.path}")

        actual = (
            target.filesystem.read_text(self.path, root=self.root)
            if target.filesystem.exists(self.path, root=self.root)
            else None
        )

        if not self.watched:
            if actual != self.content:
                self._write(target, self.content)
            return

        cached = target.watch.get(self.path)

        if actual == self.content:
            target.watch.record(
                self.path,
                self.content,
                root=self.root,
            )
            return

        if cached is None:
            if actual is None:
                self._write(target, self.content)
                target.watch.record(
                    self.path,
                    self.content,
                    root=self.root,
                )
                return

            target.output.warning(
                f"Watched file exists without cached state: {self.path}"
            )
            target.watch.show_diff(
                self.path,
                actual,
                self.content,
                before_name="actual",
                after_name="desired",
            )

            action = _watch_action(
                target,
                can_restore=False,
                can_apply=True,
            )

            if action == "keep":
                return

            self._write(target, self.content)
            target.watch.record(
                self.path,
                self.content,
                root=self.root,
            )
            return

        if actual == cached.content:
            self._write(target, self.content)
            target.watch.record(
                self.path,
                self.content,
                root=self.root,
            )
            return

        target.output.warning(
            f"Watched file changed since phs last wrote it: {self.path}"
        )
        target.watch.show_diff(
            self.path,
            cached.content,
            actual or "",
            before_name="cached",
            after_name="actual",
        )

        phs_changed = self.content != cached.content

        if phs_changed:
            target.output.info("phs also wants to change this file:")
            target.watch.show_diff(
                self.path,
                cached.content,
                self.content,
                before_name="cached",
                after_name="desired",
            )

        action = _watch_action(
            target,
            can_restore=True,
            can_apply=phs_changed,
        )

        if action == "keep":
            target.watch.preserve(self.path)
            return

        if action == "restore":
            self._write(target, cached.content)
            target.watch.record(
                self.path,
                cached.content,
                root=self.root,
            )
            return

        self._write(target, self.content)
        target.watch.record(
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


@final
class File:
    @staticmethod
    def write(
        path: Path,
        content: str,
        *,
        root: bool = False,
        as_given: bool = False,
        watched: bool = False,
    ) -> Task:
        if not as_given:
            content = dedent(content).strip() + "\n"

        return FileWrite(
            path=path,
            content=content,
            root=root,
            watched=watched,
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
