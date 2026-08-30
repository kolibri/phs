from collections.abc import Sequence
from typing import final

from phs.modules.task import Task
from phs.target.base import Target


@final
class Executor:
    @staticmethod
    def execute(
        tasks: Sequence[Task],
        target: Target,
    ) -> None:
        for task in tasks:
            task.execute(target)
