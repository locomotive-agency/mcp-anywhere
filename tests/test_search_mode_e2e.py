"""Search mode end to end, through a real MCP client and real mounted servers.

Unit tests pin the pieces; this file pins what a client actually experiences: which
tools it is offered, that a hidden tool runs through call_tool with its result
intact, that errors come back as tool errors, and how many upstream lookups each
request costs -- the review that shaped this found the meta tools repeating the full
fan-out two to three times over.
"""

import logging

import pytest
from fastmcp import Client, FastMCP

from mcp_anywhere.core import tool_search as ts
from mcp_anywhere.core.tool_routing import install_prefix_routing
from mcp_anywhere.core.tool_search import ToolEntry, register_search_tool

logging.getLogger("mcp_anywhere").setLevel(logging.CRITICAL)


def build_router(n_servers=5, counts=None):
    router = FastMCP("router")
    for i in range(n_servers):
        child = FastMCP(f"child{i}")

        @child.tool(name="echo")
        def echo(text: str, _i=i) -> str:
            """Echo the text back."""
            return f"{_i}:{text}"

        @child.tool(name="fail")
        def fail() -> str:
            """Always fail."""
            raise ValueError("inner tool failed on purpose")

        if counts is not None:
            for attr in ("get_tools", "list_tools"):
                orig = getattr(child._tool_manager, attr)

                async def counted(_orig=orig, _i=i):
                    counts[_i] = counts.get(_i, 0) + 1
                    return await _orig()

                setattr(child._tool_manager, attr, counted)
        router.mount(child, prefix=f"s{i:07d}")
    return router


def fake_catalogue(n_servers, unmounted=()):
    out = []
    for i in range(n_servers):
        for tool in ("echo", "fail"):
            out.append(ToolEntry(qualified_name=f"s{i:07d}_{tool}", server_name=f"server-{i}",
                                 tool_name=tool, description=f"{tool} on server {i}",
                                 schema={"properties": {"text": {"type": "string"}}}))
    for sid in unmounted:
        out.append(ToolEntry(qualified_name=f"{sid}_ghost", server_name="ghost-server",
                             tool_name="ghost", description="on a server that failed to mount"))
    return out


@pytest.fixture
def catalogue(monkeypatch):
    """Stand in for the database: every mounted tool, plus one on an unmounted server."""
    # Enough servers for the fan-out tests; the others mount only the first five.
    cat = fake_catalogue(20, unmounted=("deadbeef",))

    async def load(user_id=None):
        return cat

    monkeypatch.setattr(ts, "load_catalogue", load)
    return cat


def text_of(result):
    return "".join(getattr(c, "text", "") for c in result.content)


class TestWhatTheClientSees:
    async def test_meta_tools_are_listed_without_an_output_schema(self, catalogue):
        """No output schema: text arrives as text, and call_tool can pass any result."""
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            tools = {t.name: t for t in await c.list_tools()}
        for meta in ("search_tools", "describe_tool", "call_tool"):
            assert meta in tools
            assert tools[meta].outputSchema is None

    async def test_search_results_are_plain_text(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("search_tools", {"query": "echo"})
        assert text_of(res).startswith(("Showing", "5 of")), text_of(res)[:80]
        assert '{"result"' not in text_of(res)


class TestCallTool:
    async def test_a_tool_runs_through_call_tool_with_its_result_intact(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("call_tool", {"name": "s0000003_echo", "arguments": {"text": "hi"}})
        assert text_of(res) == "3:hi"

    async def test_arguments_may_arrive_as_json_text(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("call_tool", {"name": "s0000001_echo", "arguments": '{"text": "x"}'})
        assert text_of(res) == "1:x"

    async def test_an_inner_failure_is_a_tool_error_with_the_reason(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("call_tool", {"name": "s0000002_fail"}, raise_on_error=False)
        assert res.is_error
        assert "failed on purpose" in text_of(res)

    async def test_an_unknown_name_is_refused(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("call_tool", {"name": "s0000002_nope"}, raise_on_error=False)
        assert res.is_error and "search_tools" in text_of(res)

    async def test_a_server_that_failed_to_mount_is_not_offered(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            found = text_of(await c.call_tool("search_tools", {"query": "ghost"}))
            res = await c.call_tool("call_tool", {"name": "deadbeef_ghost"}, raise_on_error=False)
        assert "deadbeef_ghost" not in found
        assert res.is_error

    async def test_describe_tool_returns_the_schema(self, catalogue):
        router = build_router()
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(5)})
        async with Client(router) as c:
            res = await c.call_tool("describe_tool", {"name": "s0000000_echo"})
        assert '"text"' in text_of(res) and "server-0" in text_of(res)


class TestFanOut:
    """Upstream lookups per request, with a client that listed first as real ones do."""

    N = 20

    async def _count(self, patched, method, args):
        counts = {}
        router = build_router(self.N, counts)
        register_search_tool(router, mounted_ids=lambda: {f"s{i:07d}" for i in range(self.N)})
        if patched:
            install_prefix_routing(router)
        async with Client(router) as c:
            await c.list_tools()
            counts.clear()
            await c.call_tool(method, args)
        return sum(counts.values()), len(counts)

    async def test_a_direct_call_asks_only_the_owning_server(self, catalogue):
        unpatched, _ = await self._count(False, "s0000007_echo", {"text": "a"})
        patched, servers = await self._count(True, "s0000007_echo", {"text": "a"})
        assert servers == 1, "only the owning server is asked"
        assert unpatched >= self.N, "without routing every server is asked"
        assert patched < unpatched

    async def test_call_tool_asks_only_the_owning_server(self, catalogue):
        _, servers = await self._count(True, "call_tool", {"name": "s0000007_echo", "arguments": {"text": "a"}})
        assert servers == 1

    async def test_search_asks_no_server_at_all(self, catalogue):
        lookups, _ = await self._count(True, "search_tools", {"query": "echo"})
        assert lookups == 0, "search reads the database, never the servers"


class TestPrefixRoutingFallbacks:
    async def test_an_unprefixed_mount_falls_back_to_fastmcps_own_lookup(self):
        router = FastMCP("router")
        child = FastMCP("c")

        @child.tool(name="plain")
        def plain() -> str:
            return "ok"

        router.mount(child)  # no prefix: could own any key
        assert install_prefix_routing(router)
        tool = await router._tool_manager.get_tool("plain")
        assert tool.key == "plain"

    async def test_installing_twice_is_harmless(self):
        router = build_router(2)
        assert install_prefix_routing(router) and install_prefix_routing(router)

    async def test_unexpected_internals_leave_fastmcp_alone(self):
        class NotARouter:
            pass

        assert install_prefix_routing(NotARouter()) is False
