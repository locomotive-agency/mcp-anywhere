"""Cache for the aggregated tools/list."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from mcp_anywhere.config import Config
from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)


class ToolListCache:
    """Holds the tool catalogue produced by asking every mounted server.

    A tools/list is answered by aggregating across all mounted proxies, so its cost
    scales with the number of servers rather than with the request: on a gateway
    fronting a few dozen stdio servers one listing takes seconds, and every client
    pays that again on connect. The catalogue itself only changes when a server is
    mounted or unmounted, which makes it unusually cheap to hold.

    What is cached is deliberately the *unfiltered* list. Per-user filtering stays on
    the request path, so caching can never widen what a caller is allowed to see.

    Off by default: a gateway with two servers gains nothing from it, and a cache
    nobody asked for only buys the chance of a stale answer. Set
    TOOL_LIST_CACHE_TTL to a positive number of seconds to enable it.
    """

    def __init__(
        self, ttl: float | None = None, now: Callable[[], float] = time.monotonic
    ) -> None:
        """Build a cache holding the catalogue for ``ttl`` seconds (0 disables it)."""
        self._ttl = float(Config.TOOL_LIST_CACHE_TTL if ttl is None else ttl)
        # Injectable so a test can drive expiry without touching the global clock --
        # patching time.monotonic would also move the event loop's clock and hang any
        # test that awaits a timer.
        self._now = now
        self._value: list[Any] | None = None
        self._expires_at = 0.0
        # Serialises population so that N clients arriving at once pay for one
        # aggregation between them instead of N.
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    @property
    def enabled(self) -> bool:
        """Whether caching is switched on at all."""
        return self._ttl > 0

    @property
    def stats(self) -> dict[str, Any]:
        """Hit/miss counters, for logging and tests."""
        return {"hits": self._hits, "misses": self._misses, "ttl": self._ttl}

    def invalidate(self, reason: str = "") -> None:
        """Drop the cached catalogue so the next listing rebuilds it."""
        if self._value is None:
            return
        self._value = None
        self._expires_at = 0.0
        logger.info(f"Tool list cache invalidated{f' ({reason})' if reason else ''}")

    async def get_or_populate(
        self, produce: Callable[[], Awaitable[list[Any]]]
    ) -> list[Any]:
        """Return the cached catalogue, producing it first if it is not fresh.

        A failing ``produce`` is never cached: the exception propagates and the next
        caller tries again, so a momentarily unreachable server cannot pin an error
        in place for the length of the TTL.
        """
        if not self.enabled:
            return await produce()

        cached = self._fresh()
        if cached is not None:
            self._hits += 1
            return cached

        async with self._lock:
            # Someone may have populated it while this caller waited for the lock.
            cached = self._fresh()
            if cached is not None:
                self._hits += 1
                return cached

            self._misses += 1
            value = await produce()
            self._value = value
            self._expires_at = self._now() + self._ttl
            return value

    def _fresh(self) -> list[Any] | None:
        if self._value is None or self._now() >= self._expires_at:
            return None
        return self._value


# Shared by the middleware that reads the catalogue and the manager that changes it.
tool_list_cache = ToolListCache()
