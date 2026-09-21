"""The tools/list cache.

A listing fans out to every mounted server, so its cost tracks the number of servers
rather than the request. These tests pin the properties that make holding it safe:
it is off unless asked for, it never serves a catalogue past its TTL or across a
mount change, concurrent callers pay for one aggregation between them, and a failure
is never cached.
"""

import asyncio

import pytest

from mcp_anywhere.core import tool_cache as tc
from mcp_anywhere.core.tool_cache import ToolListCache


class Clock:
    """A clock the test drives.

    Injected rather than monkeypatched: time.monotonic is also the event loop's
    clock, so replacing it globally hangs any test that awaits a timer.
    """

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def clock():
    return Clock()


def counting_producer(value=None):
    calls = {"n": 0}

    async def produce():
        calls["n"] += 1
        return value if value is not None else [f"tool-{calls['n']}"]

    return produce, calls


class TestDisabledByDefault:
    async def test_ttl_zero_never_caches(self, clock):
        cache = ToolListCache(now=clock, ttl=0)
        produce, calls = counting_producer()
        assert not cache.enabled
        for _ in range(3):
            await cache.get_or_populate(produce)
        assert calls["n"] == 3

    async def test_module_singleton_is_off_unless_configured(self):
        """The shipped default must not change behaviour for existing deployments."""
        assert tc.tool_list_cache.enabled is False


class TestCaching:
    async def test_second_call_is_served_from_cache(self, clock):
        cache = ToolListCache(now=clock, ttl=30)
        produce, calls = counting_producer(["a", "b"])
        first = await cache.get_or_populate(produce)
        second = await cache.get_or_populate(produce)
        assert calls["n"] == 1
        assert first == second == ["a", "b"]
        assert cache.stats["hits"] == 1 and cache.stats["misses"] == 1

    async def test_rebuilds_after_ttl_expires(self, clock):
        cache = ToolListCache(now=clock, ttl=30)
        produce, calls = counting_producer()
        await cache.get_or_populate(produce)
        clock.advance(29)
        await cache.get_or_populate(produce)
        assert calls["n"] == 1, "still inside the TTL"
        clock.advance(2)
        await cache.get_or_populate(produce)
        assert calls["n"] == 2, "TTL elapsed, must rebuild"

    async def test_expiry_boundary_is_not_stale(self, clock):
        cache = ToolListCache(now=clock, ttl=10)
        produce, calls = counting_producer()
        await cache.get_or_populate(produce)
        clock.advance(10)  # exactly at the boundary
        await cache.get_or_populate(produce)
        assert calls["n"] == 2


class TestInvalidation:
    async def test_invalidate_forces_a_rebuild(self, clock):
        cache = ToolListCache(now=clock, ttl=300)
        produce, calls = counting_producer()
        await cache.get_or_populate(produce)
        cache.invalidate("server mounted")
        await cache.get_or_populate(produce)
        assert calls["n"] == 2

    async def test_invalidating_an_empty_cache_is_a_noop(self, clock):
        ToolListCache(now=clock, ttl=300).invalidate("nothing held")  # must not raise

    async def test_a_mount_must_not_be_hidden_by_a_long_ttl(self, clock):
        """The scenario the invalidation hooks exist for."""
        cache = ToolListCache(now=clock, ttl=86400)
        produce, calls = counting_producer()
        assert await cache.get_or_populate(produce) == ["tool-1"]
        cache.invalidate("mounted 'new-server'")
        assert await cache.get_or_populate(produce) == ["tool-2"]


class TestConcurrency:
    async def test_concurrent_callers_aggregate_once(self, clock):
        """Without single-flight, N clients connecting at once each pay the full cost."""
        cache = ToolListCache(now=clock, ttl=60)
        calls = {"n": 0}
        started = asyncio.Event()

        async def slow_produce():
            calls["n"] += 1
            started.set()
            await asyncio.sleep(0.05)
            return ["only-once"]

        results = await asyncio.gather(*(cache.get_or_populate(slow_produce) for _ in range(8)))
        assert calls["n"] == 1
        assert all(r == ["only-once"] for r in results)


class TestFailures:
    async def test_an_exception_is_not_cached(self, clock):
        cache = ToolListCache(now=clock, ttl=300)
        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("unreachable")
            return ["recovered"]

        with pytest.raises(RuntimeError):
            await cache.get_or_populate(flaky)
        assert await cache.get_or_populate(flaky) == ["recovered"]
        assert calls["n"] == 2

    async def test_an_empty_catalogue_is_still_a_valid_answer(self, clock):
        cache = ToolListCache(now=clock, ttl=60)
        produce, calls = counting_producer([])
        assert await cache.get_or_populate(produce) == []
        assert await cache.get_or_populate(produce) == []
        assert calls["n"] == 1, "an empty list must not be mistaken for 'not cached'"
