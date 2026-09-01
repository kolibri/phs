from collections.abc import Sequence
from typing import final

from phs.target.context import TargetContext
from phs.tasks.task import Task


@final
class Executor:
    @staticmethod
    def execute(
            tasks: Sequence[Task],
            target: TargetContext,
    ) -> None:
        for task in tasks:
            task.execute(target)
