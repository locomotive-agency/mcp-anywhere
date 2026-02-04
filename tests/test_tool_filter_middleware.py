"""
Test the ToolFilterMiddleware.

This module tests the moved and refactored ToolFilterMiddleware as specified
in Phase 3 of the engineering documentation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.testing import skip_test

from mcp_anywhere.auth.models import User, UserToolPermission
from mcp_anywhere.core.middleware import ToolFilterMiddleware


@pytest.mark.asyncio
async def test_tool_filter_middleware_initialization():
    """
    Test that ToolFilterMiddleware can be initialized properly.
    """
    middleware = ToolFilterMiddleware()
    assert isinstance(middleware, ToolFilterMiddleware)


@pytest.mark.asyncio
async def test_tool_filter_middleware_passthrough_when_no_disabled_tools():
    """
    When there are no disabled tools, on_list_tools should return the original list.
    """

    middleware = ToolFilterMiddleware()
    tools = [
        {"name": "enabled_tool", "description": "An enabled tool"},
        {"name": "another_enabled_tool", "description": "Another enabled tool"},
    ]

    # Mock context and call_next
    mock_context = Mock()
    mock_call_next = AsyncMock(return_value=tools)

    # No disabled tools
    with patch.object(
        ToolFilterMiddleware,
        "_get_disabled_tools_async",
        new=AsyncMock(return_value=set()),
    ):
        result = await middleware.on_list_tools(mock_context, mock_call_next)
        assert result == tools
        mock_call_next.assert_called_once_with(mock_context)


@pytest.mark.asyncio
async def test_tool_filter_middleware_filters_disabled_tools():
    """
    Test that the middleware filters out disabled tools from the tools list.
    """
    tools = [
        {"name": "enabled_tool", "description": "An enabled tool"},
        {"name": "disabled_tool", "description": "A disabled tool"},
        {"name": "another_enabled_tool", "description": "Another enabled tool"},
    ]

    middleware = ToolFilterMiddleware()

    # Mock context with proper nested structure
    mock_user = {"id": "test-user-id", "username": "testuser"}
    mock_request = Mock()
    mock_request.state.user = mock_user

    mock_fastmcp_context = Mock()
    mock_fastmcp_context.get_http_request.return_value = mock_request

    mock_context = Mock()
    mock_context.fastmcp_context = mock_fastmcp_context

    mock_call_next = AsyncMock(return_value=tools)

    with patch.object(
        ToolFilterMiddleware,
        "_get_disabled_tools_async",
        new=AsyncMock(return_value={"disabled_tool"}),
    ):
        with patch.object(
            ToolFilterMiddleware,
            "_get_denied_tools_async",
            new=AsyncMock(return_value=set()),  # No denied tools for this user
        ):
            filtered = await middleware.on_list_tools(mock_context, mock_call_next)
            tool_names = {
                t["name"] if isinstance(t, dict) else getattr(t, "name", "") for t in filtered
            }
            assert "disabled_tool" not in tool_names
            mock_call_next.assert_called_once_with(mock_context)


@pytest.mark.asyncio
async def test_get_disabled_tools_from_database():
    """
    Test that disabled tools are correctly queried from the database using a real test database.
    """
    import os
    import tempfile

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker

    from mcp_anywhere.base import Base
    from mcp_anywhere.database import MCPServerTool

    # Create a temporary SQLite database for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        # Create async engine for test database
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        # Create tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Insert test data
        async with (TestSessionLocal() as session):
            # Create some enabled and disabled tools

            enabled_tool_1 = MCPServerTool(
                    tool_name="enabled_tool_1",
                    server_id="server1",
                    tool_description="Enabled tool 1",
                    is_enabled=True,
                )

            disabled_tool_1 = MCPServerTool(
                    tool_name="disabled_tool_1",
                    server_id="server1",
                    tool_description="Disabled tool 1",
                    is_enabled=False,
                )

            disabled_tool_2 = MCPServerTool(
                    tool_name="disabled_tool_2",
                    server_id="server1",
                    tool_description="Disabled tool 2",
                    is_enabled=False,
                )

            allowed_tool_1 = MCPServerTool(
                    tool_name="allowed_tool_1",
                    server_id="server2",
                    tool_description="Allowed tool 1",
                    is_enabled=True,
                )

            denied_tool_2 = MCPServerTool(
                tool_name="denied_tool_2",
                server_id="server2",
                tool_description="Denied tool 2",
                is_enabled=True,
            )

            user = User(username="testuser", role="user")
            user.set_password("testpassword")
            user.id = "1"
            session.add(user)
            await session.flush()

            session.add_all([enabled_tool_1, disabled_tool_1, disabled_tool_2, allowed_tool_1, denied_tool_2])
            await session.commit()
            await session.flush()

            # Create permissions
            perm1 = UserToolPermission(user_id=user.id, tool_id=enabled_tool_1.id, permission="deny")
            perm2 = UserToolPermission(user_id=user.id, tool_id=disabled_tool_1.id, permission="deny")
            perm3 = UserToolPermission(user_id=user.id, tool_id=allowed_tool_1.id, permission="allow")
            perm4 = UserToolPermission(user_id=user.id, tool_id=denied_tool_2.id, permission="deny")
            session.add_all([perm1, perm2, perm3, perm4])
            await session.commit()

        # Create a proper async context manager mock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        # Patch get_async_session to use our test database
        with patch(
            "mcp_anywhere.core.middleware.get_async_session", side_effect=mock_session_context
        ):
            user_id = "1"
            # Test the actual method
            middleware = ToolFilterMiddleware()
            disabled_tools = await middleware._get_disabled_tools_async()

            # Should return only the disabled tool names
            expected_disabled = {"disabled_tool_1", "disabled_tool_2"}
            expected_denied_tools = {"disabled_tool_1", "enabled_tool_1", "denied_tool_2"}
            expected_combined = {"disabled_tool_1", "disabled_tool_2", "enabled_tool_1", "denied_tool_2"}
            assert disabled_tools == expected_disabled

            denied_tools = await middleware._get_denied_tools_async(user_id)
            assert denied_tools == expected_denied_tools

            combined = disabled_tools.union(denied_tools)
            assert combined == expected_combined

        # Cleanup
        await test_engine.dispose()

    finally:
        # Remove temporary database file
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_middleware_handles_database_errors():
    """
    If database access fails, on_list_tools should return the original list.
    """
    middleware = ToolFilterMiddleware()
    tools = [
        {"name": "enabled_tool"},
        {"name": "maybe_disabled_tool"},
    ]

    # Mock context and call_next
    mock_context = Mock()
    mock_call_next = AsyncMock(return_value=tools)

    with patch.object(
        ToolFilterMiddleware,
        "_get_disabled_tools_async",
        new=AsyncMock(side_effect=Exception("DB failure")),
    ):
        result = await middleware.on_list_tools(mock_context, mock_call_next)
        assert result == tools
        mock_call_next.assert_called_once_with(mock_context)


@pytest.mark.asyncio
async def test_tool_filtering_logic():
    """
    Test the tool filtering logic with various tool formats.
    """
    middleware = ToolFilterMiddleware()

    # Test tools in different formats
    enabled_tool_mock = Mock()
    enabled_tool_mock.name = "another_enabled_tool"
    disabled_tool_mock = Mock()
    disabled_tool_mock.name = "another_disabled_tool"

    tools = [
        {"name": "enabled_tool"},
        {"name": "disabled_tool"},
        enabled_tool_mock,
        disabled_tool_mock,
    ]

    disabled_tools = {"disabled_tool", "another_disabled_tool"}

    filtered_tools = middleware._filter_tools(tools, disabled_tools)

    # Should only have enabled tools
    assert len(filtered_tools) == 2

    # Check that disabled tools are filtered out
    tool_names = []
    for tool in filtered_tools:
        if hasattr(tool, "name"):
            tool_names.append(tool.name)
        elif isinstance(tool, dict) and "name" in tool:
            tool_names.append(tool["name"])

    assert "enabled_tool" in tool_names
    assert "another_enabled_tool" in tool_names
    assert "disabled_tool" not in tool_names
    assert "another_disabled_tool" not in tool_names
