from typing import Protocol

from phs.target.base import Target


class Task(Protocol):
    def execute(self, target: Target) -> None:
        ...
