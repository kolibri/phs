from dataclasses import dataclass

from phs.output import Output
from phs.target.filesystem import Filesystem
from phs.target.runner import Runner
from phs.target.transfer import Transfer


@dataclass(frozen=True, slots=True)
class TargetContext:
    runner: Runner
    filesystem: Filesystem
    transfer: Transfer
    output: Output