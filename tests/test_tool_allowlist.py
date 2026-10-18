"""Client catalog limits must not leak across clients or widen existing listings."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.server.context import Context

from mcp_anywhere.core import middleware as mw
from mcp_anywhere.core.tool_cache import ToolListCache


@pytest.fixture
def headers(monkeypatch):
    current = {}
    monkeypatch.setattr(mw, "get_http_headers", lambda: current)
    return current


def context(user=None):
    request = SimpleNamespace(state=SimpleNamespace(user=user))
    return SimpleNamespace(
        fastmcp_context=SimpleNamespace(get_http_request=lambda: request)
    )


@pytest.mark.parametrize("value", ["", " , ", "unknown", "memory_*", "MEMORY_recall"])
async def test_empty_unknown_and_patterns_never_expand_to_the_catalog(headers, value):
    headers["X-MCP-Tool-Allowlist"] = value
    tools = [{"name": "memory_recall"}, {"name": "memory_delete"}]
    result = await mw.ToolFilterMiddleware().on_list_tools(
        context(), AsyncMock(return_value=tools)
    )
    assert result == []


async def test_large_catalog_is_trimmed_before_the_client_receives_it(headers):
    tools = [{"name": f"server_tool_{i}"} for i in range(2500)]
    headers["x-mcp-tool-allowlist"] = ",".join(t["name"] for t in tools[:10])
    result = await mw.ToolFilterMiddleware().on_list_tools(
        context(), AsyncMock(return_value=tools)
    )
    assert result == tools[:10]
    assert len(tools) == 2500


def test_exact_mounted_key_wins_over_same_bare_name(headers):
    first = SimpleNamespace(key="first_recall", name="recall")
    second = SimpleNamespace(key="second_recall", name="recall")
    tools = [first, second, {"name": "third_recall"}]
    headers["X-McP-ToOl-AlLoWlIsT"] = " second_recall, third_recall,second_recall, "
    assert mw._apply_requested_allowlist(tools) == [second, tools[2]]


async def test_cached_catalog_is_not_narrowed_for_other_clients(headers, monkeypatch):
    cache = ToolListCache(ttl=60)
    monkeypatch.setattr(mw, "tool_list_cache", cache)
    tools = [{"name": "first_recall"}, {"name": "second_recall"}]
    producer = AsyncMock(return_value=tools)
    middleware = mw.ToolFilterMiddleware()

    headers["X-MCP-Tool-Allowlist"] = "first_recall"
    assert await middleware.on_list_tools(context(), producer) == tools[:1]
    headers["X-MCP-Tool-Allowlist"] = "second_recall"
    assert await middleware.on_list_tools(context(), producer) == tools[1:]
    headers.clear()
    assert await middleware.on_list_tools(context(), producer) == tools
    assert producer.await_count == 1
    assert len(tools) == 2


async def test_allowlist_cannot_reintroduce_disabled_or_denied_tools(headers, monkeypatch):
    tools = [{"name": n} for n in ("allowed", "disabled", "denied")]
    headers["X-MCP-Tool-Allowlist"] = "allowed,disabled,denied"
    middleware = mw.ToolFilterMiddleware()
    monkeypatch.setattr(middleware, "_get_disabled_tools_async", AsyncMock(return_value={"disabled"}))
    monkeypatch.setattr(middleware, "_get_denied_tools_async", AsyncMock(return_value={"denied"}))
    result = await middleware.on_list_tools(context({"id": 1}), AsyncMock(return_value=tools))
    assert result == tools[:1]


async def test_database_error_still_applies_client_catalog_selection(headers, monkeypatch):
    tools = [{"name": "memory_recall"}, {"name": "other_tool"}]
    headers["X-MCP-Tool-Allowlist"] = "memory_recall"
    middleware = mw.ToolFilterMiddleware()
    monkeypatch.setattr(middleware, "_get_disabled_tools_async", AsyncMock(side_effect=RuntimeError("DB unavailable")))
    result = await middleware.on_list_tools(context({"id": 1}), AsyncMock(return_value=tools))
    assert result == tools[:1]


async def test_real_client_lists_selected_mounted_tool_and_calls_it(headers, monkeypatch):
    """Exercise the protocol and mounted tool names, not just the filter helper."""
    router = FastMCP("gateway")
    child = FastMCP("memory")

    @child.tool
    def recall(text: str) -> str:
        """Return the supplied text."""
        return text

    @child.tool
    def unlisted_echo() -> str:
        """Return a fixed string without side effects."""
        return "still callable"

    router.mount(child, prefix="memory")
    router.add_middleware(mw.ToolFilterMiddleware())
    request = SimpleNamespace(state=SimpleNamespace(user=None))
    monkeypatch.setattr(Context, "get_http_request", lambda self: request)
    headers["X-MCP-Tool-Allowlist"] = "memory_recall"

    async with Client(router) as client:
        assert [tool.name for tool in await client.list_tools()] == ["memory_recall"]
        result = await client.call_tool("memory_recall", {"text": "ok"})
        assert result.content[0].text == "ok"
        # Explicitly verify the documented boundary: selection is not authorization.
        result = await client.call_tool("memory_unlisted_echo", {})
        assert result.content[0].text == "still callable"
        headers.clear()
        assert {tool.name for tool in await client.list_tools()} == {
            "memory_recall", "memory_unlisted_echo"
        }
