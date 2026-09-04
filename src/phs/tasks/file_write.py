from dataclasses import InitVar, dataclass
from pathlib import Path
from textwrap import dedent
from typing import Literal, final

from phs.target.context import TargetContext


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
    root: bool = False
    watched: bool = False
    as_given: InitVar[bool] = False

    def __post_init__(self, as_given: bool) -> None:
        if not as_given:
            object.__setattr__(self, "content", dedent(self.content).strip() + "\n")

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
