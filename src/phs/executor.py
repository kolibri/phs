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
        try:
            for task in tasks:
                task.execute(target)
        except Exception:
            target.watch.save(success=False)
            raise

        target.watch.save(success=True)
