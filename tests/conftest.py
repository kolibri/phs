from unittest.mock import Mock

import pytest

from phs.output import Output
from phs.target.context import TargetContext
from phs.target.filesystem import Filesystem
from phs.target.runner import Runner
from phs.target.transfer import Transfer
from phs.watch import WatchCache


@pytest.fixture
def target() -> TargetContext:
    return TargetContext(
        runner=Mock(spec=Runner),
        filesystem=Mock(spec=Filesystem),
        transfer=Mock(spec=Transfer),
        output=Mock(spec=Output),
        watch=Mock(spec=WatchCache),
    )
