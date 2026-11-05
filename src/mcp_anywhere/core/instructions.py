"""The instructions the gateway sends every client when it initializes."""

import asyncio
from pathlib import Path

from fastmcp import FastMCP

from mcp_anywhere.config import Config
from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)

# Unchanged upstream text: what a gateway without search, and without an operator
# addendum, has always sent.
BASE_INSTRUCTIONS = (
    "This router provides access to multiple MCP servers.\n"
    "        \n"
    "All tools from mounted servers are available directly with prefixed names.\n"
    "You can use tools/list to see all available tools from all mounted servers.\n"
)

# An operator addendum is free text, but it is sent to every client on every
# connect, so it is capped rather than trusted to stay small.
_EXTRA_MAX_CHARS = 8000


def build_instructions(
    servers: list[tuple[str, str, int]],
    search_enabled: bool,
    extra: str = "",
) -> str:
    """Compose the instructions from the mounted servers and the operator addendum.

    Args:
        servers: (server_id, friendly name, enabled tool count) for each active server.
        search_enabled: Whether search_tools, describe_tool and call_tool exist.
        extra: Operator-supplied text, e.g. which servers belong to which organisation.
            Empty for none.

    Order matters. Claude Code cuts server instructions at 2048 characters by default
    (CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH), and a table of a few dozen servers runs
    past that on its own. So the guidance comes first, the operator's addendum second,
    and the id table last: truncation then costs the tail of the table, which
    search_tools repeats per result anyway, instead of the guidance or the addendum.
    """
    extra = (extra or "").strip()
    if not search_enabled:
        return f"{BASE_INSTRUCTIONS.rstrip()}\n\n{extra}\n" if extra else BASE_INSTRUCTIONS

    total = sum(count for _, _, count in servers)
    guidance = f"""MCP Anywhere gateway: {len(servers)} servers, {total} tools.
Tools are named "<server-id>_<tool>"; the id is opaque, and several servers are
separate instances of the same software for different organisations. A tool with the
same name on two servers acts on two different systems: choose by server name, and ask
the user when the request does not make the target clear.

- search_tools(query, limit, server): find tools by keyword; each result shows its
  callable name, parameters and the server it acts on.
- describe_tool(name): the full input schema of one tool.
- call_tool(name, arguments): run any tool by its full name. Use it for tools missing
  from your tool list; this gateway may list only these three."""
    parts = [guidance]
    if extra:
        parts.append(extra)
    table = "; ".join(
        f"{sid} {name} ({count})"
        for sid, name, count in sorted(servers, key=lambda s: s[1].lower())
    )
    parts.append(f"Server ids: {table}")
    return "\n\n".join(parts) + "\n"


def read_extra_instructions(path: str) -> str:
    """Read the operator addendum, or "" when none is configured or it is unreadable."""
    if not path:
        return ""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"ROUTER_INSTRUCTIONS_FILE {path!r} could not be read: {e}")
        return ""
    if len(content) > _EXTRA_MAX_CHARS:
        logger.warning(
            f"ROUTER_INSTRUCTIONS_FILE is {len(content)} chars; "
            f"sending the first {_EXTRA_MAX_CHARS}"
        )
        content = content[:_EXTRA_MAX_CHARS]
    return content


async def load_server_summary() -> list[tuple[str, str, int]]:
    """(id, name, enabled tool count) for every active server."""
    from sqlalchemy import text

    from mcp_anywhere.database import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT s.id, s.name,
                       COALESCE(SUM(CASE WHEN t.is_enabled = 1 THEN 1 ELSE 0 END), 0)
                FROM mcp_servers s
                LEFT JOIN mcp_server_tools t ON t.server_id = s.id
                WHERE s.is_active = 1
                GROUP BY s.id, s.name
                """
            )
        )
        return [(str(r[0]), str(r[1]), int(r[2])) for r in result]


def set_router_instructions(router: FastMCP, text: str) -> None:
    """Replace the instructions new sessions will receive.

    FastMCP exposes instructions read-only, but the low-level server builds its
    initialization options per session, so assigning the underlying attribute reaches
    every client that connects afterwards. Sessions already open keep what they got.
    """
    router._mcp_server.instructions = text


async def refresh_router_instructions(router: FastMCP) -> None:
    """Rebuild the instructions from the database and the operator addendum.

    Never raises: stale instructions are a nuisance, a failed mount is an outage.
    """
    try:
        extra = read_extra_instructions(Config.ROUTER_INSTRUCTIONS_FILE)
        servers = (
            await load_server_summary() if Config.TOOL_SEARCH_ENABLED else []
        )
        set_router_instructions(
            router, build_instructions(servers, Config.TOOL_SEARCH_ENABLED, extra)
        )
    except Exception as e:  # noqa: BLE001 -- see docstring
        logger.warning(f"Could not refresh router instructions: {e}")


_bound_router: FastMCP | None = None
_refresh_task: asyncio.Task | None = None
_refresh_again = False


def bind_router(router: FastMCP) -> None:
    """Remember which router refreshes apply to, so callers need not carry it."""
    global _bound_router
    _bound_router = router


async def _refresh_loop() -> None:
    global _refresh_again
    while True:
        _refresh_again = False
        if _bound_router is not None:
            await refresh_router_instructions(_bound_router)
        if not _refresh_again:
            return


def schedule_instructions_refresh(router: FastMCP | None = None) -> None:
    """Refresh in the background, from code that cannot await.

    Called on every mount, unmount, tool store and toggle -- 37 times in a row at
    startup -- so requests are coalesced into one running refresh, which runs once
    more if anything asked again while it was busy. The task is held in a module
    reference: asyncio keeps only a weak one, and an unreferenced task can be
    collected before it runs.
    """
    global _refresh_task, _refresh_again
    if router is not None and _bound_router is None:
        bind_router(router)
    if _bound_router is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no loop, e.g. a synchronous test; the next refresh will catch up
    if _refresh_task is not None and not _refresh_task.done():
        _refresh_again = True
        return
    _refresh_task = loop.create_task(_refresh_loop())
