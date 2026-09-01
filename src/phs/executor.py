from collections.abc import Sequence
from typing import final

from phs.modules.task import Task
from phs.target.context import TargetContext


@final
class Executor:
    @staticmethod
    def execute(
        tasks: Sequence[Task],
        target: TargetContext,
    ) -> None:
        for task in tasks:
            task.execute(target)
