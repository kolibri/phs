from typing import Protocol

from phs.target.context import TargetContext


class Task(Protocol):
    def execute(self, target: TargetContext) -> None:
        ...
