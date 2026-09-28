"""Resolve a tool through the one mounted server that owns it."""

from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.tools import Tool

from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)


def install_prefix_routing(router: FastMCP) -> bool:
    """Make the router look a tool up in its owning server instead of in all of them.

    FastMCP's ToolManager.get_tool builds the complete inventory -- a tools/list on
    every mounted server -- and then picks one key out of it. The router calls it on
    every tools/call, so on a gateway with N stdio servers each call costs N upstream
    listings before it reaches the one server that runs it. mcp-anywhere mounts every
    server under a unique id prefix, so the owner of "afc9d618_create_issue" is known
    from the key alone and only that server needs asking.

    The replacement falls back to the original lookup for anything it cannot resolve
    by prefix: an unprefixed mount (which could own any key), a router with tool
    transformations, or a key no prefix matches.

    This reaches into FastMCP internals (_tool_manager, _mounted_servers, prefix,
    server), which are private and not pinned. If they are not shaped as expected the
    patch is not installed and lookups keep FastMCP's own behaviour.

    Returns:
        True if installed (or already installed), False if left alone.
    """
    tm = getattr(router, "_tool_manager", None)
    if tm is None or not hasattr(tm, "_mounted_servers") or not hasattr(tm, "_tools"):
        logger.warning("Prefix routing not installed: unexpected FastMCP internals")
        return False
    if getattr(tm, "_mcpa_prefix_routing", False):
        return True

    original_get_tool = tm.get_tool

    async def get_tool(key: str) -> Tool:
        local = tm._tools.get(key)
        if local is not None and not getattr(tm, "transformations", None):
            return local
        if getattr(tm, "transformations", None):
            return await original_get_tool(key)
        # Last mounted wins, as in FastMCP's own call dispatch.
        for mounted in reversed(tm._mounted_servers):
            prefix = getattr(mounted, "prefix", None)
            if not prefix:
                return await original_get_tool(key)
            if not key.startswith(f"{prefix}_"):
                continue
            try:
                tool = await mounted.server._tool_manager.get_tool(
                    key.removeprefix(f"{prefix}_")
                )
            except NotFoundError:
                continue
            return tool.with_key(key)
        return await original_get_tool(key)

    tm.get_tool = get_tool
    tm._mcpa_prefix_routing = True
    logger.info("Prefix routing installed: tool lookups ask only the owning server")
    return True
