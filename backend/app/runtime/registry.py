"""Named runtime factories; register future harnesses here without changing routers."""

from collections.abc import Callable

from .base import AgentRuntime
from .pi import PiRuntime, RuntimeFailure
from .stub import StubRuntime

RUNTIMES: dict[str, Callable[[], AgentRuntime]] = {"stub": StubRuntime, "pi": PiRuntime}


def get_runtime(name: str) -> AgentRuntime:
    factory = RUNTIMES.get(name)
    if factory is None:
        raise RuntimeFailure(
            "Unknown harness. Select pi or the explicit offline stub in Employment."
        )
    return factory()
