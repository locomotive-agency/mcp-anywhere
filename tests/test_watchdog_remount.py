"""Re-mounts done by the crash watchdog must be bounded in time.

The watchdog recovers servers one after another in a single loop. ``add_server``
mounts the proxy first and only then waits for the server to list its tools, with no
deadline of its own. A server that never answers -- an mcp-remote bridge waiting for
an OAuth login in a browser nobody will open, for instance -- therefore froze the
whole loop: no other server was recovered while it waited, and because the
half-mounted proxy stayed on the router, every aggregated ``tools/list`` hung on it
too. ``remount_server`` gives up after a deadline, takes the proxy off the router and
frees the container, so the stuck stdio client dies and the loop moves on.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from mcp_anywhere.core import mcp_manager as mm


@pytest.fixture
def server():
    s = MagicMock()
    s.id = "srv-1"
    s.name = "test-server"
    return s


@pytest.fixture
def container_manager():
    cm = MagicMock()
    cm._get_container_name.return_value = "mcp-srv-1"
    return cm


def _mcp_manager(add_server):
    m = MagicMock()
    m.add_server = add_server
    return m


async def test_a_server_that_answers_is_remounted(server, container_manager):
    async def add_server(_server):
        return [{"name": "tool"}]

    mcp_manager = _mcp_manager(add_server)

    assert await mm.remount_server(mcp_manager, container_manager, server, 1) is True
    mcp_manager.remove_server.assert_not_called()
    container_manager._cleanup_existing_container.assert_not_called()


async def test_a_server_that_never_answers_is_given_up(server, container_manager):
    async def add_server(_server):
        await asyncio.Event().wait()  # never set: the mount hangs forever

    mcp_manager = _mcp_manager(add_server)

    result = await asyncio.wait_for(
        mm.remount_server(mcp_manager, container_manager, server, 0.05), timeout=5
    )

    assert result is False
    # The half-mounted proxy must leave the router, or tools/list keeps hanging on it.
    mcp_manager.remove_server.assert_called_once_with("srv-1")
    # And the container goes, so the stuck stdio client exits with it.
    container_manager._cleanup_existing_container.assert_called_once_with("mcp-srv-1")


async def test_a_failing_mount_still_raises(server, container_manager):
    async def add_server(_server):
        raise RuntimeError("Client failed to connect")

    mcp_manager = _mcp_manager(add_server)

    with pytest.raises(RuntimeError, match="Client failed to connect"):
        await mm.remount_server(mcp_manager, container_manager, server, 1)
    mcp_manager.remove_server.assert_not_called()
