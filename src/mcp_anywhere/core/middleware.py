"""FastMCP middleware to filter tools based on database enable/disable state.

This integrates with FastMCP's middleware lifecycle (e.g., on_list_tools)
so filtering happens at the correct protocol layer, before tools are exposed.

References:
- Filtering is performed by overriding the FastMCP middleware hook that lists tools,
  similar to patterns used in related projects [server.py][1], [middleware.py][2].

"""

from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext
from sqlalchemy import select

from mcp_anywhere.auth.models import UserToolPermission
from mcp_anywhere.config import Config
from mcp_anywhere.core.tool_cache import tool_list_cache
from mcp_anywhere.core.tool_search import (
    META_TOOL_NAMES,
    SEARCH_TOOL_NAME,
    effective_list_mode,
)
from mcp_anywhere.database import MCPServerTool, get_async_session
from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)


# Only these are exposed to a client that has the full catalogue. call_tool and
# describe_tool exist for clients that do not: offered alongside the catalogue,
# call_tool would be a second name for every tool, and a client's own per-tool
# permission rules (allow this one, deny that one) would stop meaning anything.
_FULL_MODE_META = frozenset({SEARCH_TOOL_NAME})


def _tool_key(tool: object) -> str | None:
    # The router key, not the tool's own name: a mounted server may well expose a
    # tool whose bare name is "call_tool", and it must not pass for the gateway's.
    return getattr(tool, "key", None) or getattr(tool, "name", None)


def _requested_list_mode() -> str:
    """"search" or "full" for the current request; always "full" without search."""
    if not Config.TOOL_SEARCH_ENABLED:
        return "full"
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers()
    except Exception:
        headers = {}
    return effective_list_mode(Config.TOOL_LIST_MODE, headers)


def _apply_list_mode(tools: list) -> list:
    """Shape a filtered listing for the request's list mode.

    search: only the three meta tools, which reach everything else.
    full:   the catalogue plus search_tools, without call_tool and describe_tool.
    Nothing changes unless TOOL_SEARCH_ENABLED.
    """
    if not Config.TOOL_SEARCH_ENABLED:
        return tools
    if _requested_list_mode() == "search":
        return [t for t in tools if _tool_key(t) in META_TOOL_NAMES]
    return [
        t
        for t in tools
        if _tool_key(t) not in META_TOOL_NAMES or _tool_key(t) in _FULL_MODE_META
    ]


def _meta_tools_without_fanout(context: MiddlewareContext) -> list | None:
    """The router's own meta tools, read without asking any mounted server.

    The point of search mode is that a client does not pay for the catalogue on
    connect, and building the catalogue is exactly what call_next would do. Returns
    None if the router cannot be reached, in which case the caller lists normally.
    """
    server = getattr(getattr(context, "fastmcp_context", None), "fastmcp", None)
    local = getattr(getattr(server, "_tool_manager", None), "_tools", None)
    if not isinstance(local, dict):
        return None
    return [tool for key, tool in local.items() if key in META_TOOL_NAMES]


class ToolFilterMiddleware(Middleware):
    """FastMCP middleware that filters disabled tools during tools/list.

    Hooks into FastMCP's lifecycle so tools are filtered before exposure.
    """

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        """Called by FastMCP before returning the available tools list.

        Args:
            context: Middleware context from FastMCP
            call_next: Function to continue middleware chain

        Returns:
            list[Any]: Filtered list with disabled tools removed
        """

        if _requested_list_mode() == "search":
            meta = _meta_tools_without_fanout(context)
            if meta is not None:
                logger.info(f"Tool list mode 'search': advertising {len(meta)} meta tools")
                return meta

        # Get the tools from the next middleware in the chain. That call fans out to
        # every mounted server, so it is the expensive half of a listing; the cache
        # holds its result when TOOL_LIST_CACHE_TTL is set. Only the *unfiltered*
        # catalogue is cached -- the per-user filtering below still runs every time,
        # so a cache can never widen what a caller sees.
        tools = await tool_list_cache.get_or_populate(lambda: call_next(context))

        user_data = []

        if context.fastmcp_context.get_http_request().state.user:
            user_data = context.fastmcp_context.get_http_request().state.user
        else:
            logger.error(f"No user data attached to request, unable to filter user tooling")
            return _apply_list_mode(tools)

        try:
            disabled_tools = await self._get_disabled_tools_async()
            denied_tools = await self._get_denied_tools_async(user_data["id"])

            combined_tools = disabled_tools.union(denied_tools)
        except Exception as exc:  # Do not fail tool listing on DB errors
            logger.exception(f"Tool filtering skipped due to DB error: {exc}")
            return _apply_list_mode(tools)

        if not disabled_tools:
            return _apply_list_mode(tools)

        filtered = self._filter_tools(list(tools), combined_tools)
        logger.info(
            f"ToolFilterMiddleware: filtered tools to {len(filtered)} allowed / enabled items"
        )
        return _apply_list_mode(filtered)

    @staticmethod
    async def _get_disabled_tools_async() -> set[str]:
        """Query disabled tool names from the database.

        Returns:
            set[str]: Set of disabled tool names
        """
        disabled: set[str] = set()
        async with get_async_session() as db_session:
            stmt = select(MCPServerTool.tool_name).where(
                MCPServerTool.is_enabled == False
            )
            result = await db_session.execute(stmt)
            for name in result.scalars().all():
                disabled.add(name)
        logger.debug(f"Disabled tools from DB: {len(disabled)}")
        return disabled

    @staticmethod
    async def _get_denied_tools_async(user_id: str) -> set[str]:
        """Query denied user tool names from the database.

        Returns:
            set[str]: Set of denied tool names
        """
        logger.debug(f"Fetching tools from DB for user {user_id}")
        denied_tools: set[str] = set()
        async with get_async_session() as db_session:
            stmt = (
                select(MCPServerTool.tool_name)
                .join(UserToolPermission)
                .where(
                    UserToolPermission.user_id == user_id,
                    UserToolPermission.permission == "deny",
                )
            )
            result = await db_session.execute(stmt)
            for name in result.scalars().all():
                denied_tools.add(name)

        logger.debug(f"Denied tools from DB for user {user_id}: {len(denied_tools)}")
        return denied_tools

    def _filter_tools(self, tools: list[Any], denied_tools: set[str]) -> list[Any]:
        """Filter a list of tools based on denied / disabled names.

        Args:
            tools: List of tool objects or dictionaries
            denied_tools: Set of denied / disabled tool names

        Returns:
            list[Any]: Filtered list containing only enabled tools
        """
        enabled: list[Any] = []
        for tool in tools:
            if not self._is_tool_denied(tool, denied_tools):
                enabled.append(tool)
            else:
                logger.debug(f"Filtering disabled tool: {self._get_tool_name(tool)}")
        return enabled

    def _is_tool_denied(self, tool: Any, denied_tools: set[str]) -> bool:
        name = self._get_tool_name(tool)
        return bool(name and name in denied_tools)

    @staticmethod
    def _get_tool_name(tool: Any) -> str:
        if hasattr(tool, "name"):
            return tool.name
        if isinstance(tool, dict) and "name" in tool:
            return tool["name"]
        return ""
