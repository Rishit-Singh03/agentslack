"""Named runtime factories; register future harnesses here without changing routers."""

import logging
from collections.abc import Callable

from .base import AgentRuntime
from .stub import StubRuntime

logger = logging.getLogger(__name__)

RUNTIMES: dict[str, Callable[[], AgentRuntime]] = {"stub": StubRuntime}


def get_runtime(name: str) -> AgentRuntime:
    factory = RUNTIMES.get(name)
    if factory is None:
        logger.warning("Unknown agent runtime %r; falling back to stub", name)
        factory = RUNTIMES["stub"]
    return factory()
