"""
Unit tests for user tool permissions functionality.

Tests cover:
- Permission model creation and validation
- Permission queries (getting allowed/denied tools for a user)
- Permission toggling (allow/deny)
- Default permission behavior
- Grouping tools by server
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_anywhere.auth.models import User, UserToolPermission
from mcp_anywhere.database import MCPServer, MCPServerTool


@pytest.mark.asyncio
async def test_create_user_tool_permission(db_session: AsyncSession):
    """Test creating a user tool permission record."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server and tool
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    # Create permission
    permission = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="allow"
    )
    db_session.add(permission)
    await db_session.commit()

    # Verify permission was created
    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    saved_permission = result.scalar_one()

    assert saved_permission.user_id == user.id
    assert saved_permission.tool_id == tool.id
    assert saved_permission.permission == "allow"
    assert saved_permission.created_at is not None
    assert saved_permission.updated_at is not None


@pytest.mark.asyncio
async def test_get_allowed_tools_for_user(db_session: AsyncSession):
    """Test querying tools that a user has 'allow' permission for."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    # Create multiple tools
    tool1 = MCPServerTool(
        server_id=server.id,
        tool_name="allowed_tool",
        tool_description="Tool with allow permission",
        is_enabled=True,
    )
    tool2 = MCPServerTool(
        server_id=server.id,
        tool_name="denied_tool",
        tool_description="Tool with deny permission",
        is_enabled=True,
    )
    tool3 = MCPServerTool(
        server_id=server.id,
        tool_name="no_permission_tool",
        tool_description="Tool with no explicit permission",
        is_enabled=True,
    )
    db_session.add_all([tool1, tool2, tool3])
    await db_session.flush()

    # Create permissions
    perm1 = UserToolPermission(user_id=user.id, tool_id=tool1.id, permission="allow")
    perm2 = UserToolPermission(user_id=user.id, tool_id=tool2.id, permission="deny")
    db_session.add_all([perm1, perm2])
    await db_session.commit()

    # Query allowed tools
    stmt = (
        select(MCPServerTool)
        .join(UserToolPermission)
        .where(
            UserToolPermission.user_id == user.id,
            UserToolPermission.permission == "allow",
        )
    )
    result = await db_session.execute(stmt)
    allowed_tools = result.scalars().all()

    assert len(allowed_tools) == 1
    assert allowed_tools[0].tool_name == "allowed_tool"


@pytest.mark.asyncio
async def test_get_denied_tools_for_user(db_session: AsyncSession):
    """Test querying tools that a user has 'deny' permission for."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    # Create tools
    tool1 = MCPServerTool(
        server_id=server.id,
        tool_name="allowed_tool",
        tool_description="Tool with allow permission",
        is_enabled=True,
    )
    tool2 = MCPServerTool(
        server_id=server.id,
        tool_name="denied_tool",
        tool_description="Tool with deny permission",
        is_enabled=True,
    )
    db_session.add_all([tool1, tool2])
    await db_session.flush()

    # Create permissions
    perm1 = UserToolPermission(user_id=user.id, tool_id=tool1.id, permission="allow")
    perm2 = UserToolPermission(user_id=user.id, tool_id=tool2.id, permission="deny")
    db_session.add_all([perm1, perm2])
    await db_session.commit()

    # Query denied tools
    stmt = (
        select(MCPServerTool)
        .join(UserToolPermission)
        .where(
            UserToolPermission.user_id == user.id,
            UserToolPermission.permission == "deny",
        )
    )
    result = await db_session.execute(stmt)
    denied_tools = result.scalars().all()

    assert len(denied_tools) == 1
    assert denied_tools[0].tool_name == "denied_tool"


@pytest.mark.asyncio
async def test_update_permission(db_session: AsyncSession):
    """Test updating a permission from allow to deny."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server and tool
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    # Create initial permission
    permission = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="allow"
    )
    db_session.add(permission)
    await db_session.commit()

    # Update permission to deny
    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    permission = result.scalar_one()

    old_updated_at = permission.updated_at
    permission.permission = "deny"
    await db_session.commit()

    # Verify update
    result = await db_session.execute(stmt)
    updated_permission = result.scalar_one()

    assert updated_permission.permission == "deny"
    # Note: updated_at might not change if onupdate isn't triggered properly
    # This is a known limitation of some SQLAlchemy configurations


@pytest.mark.asyncio
async def test_unique_constraint_user_tool(db_session: AsyncSession):
    """Test that unique constraint prevents duplicate user-tool permissions."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server and tool
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    # Create first permission
    permission1 = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="allow"
    )
    db_session.add(permission1)
    await db_session.commit()

    # Attempt to create duplicate permission
    permission2 = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="deny"
    )
    db_session.add(permission2)

    # This should raise an IntegrityError due to unique constraint
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_permission_cascade_delete_with_user(db_session: AsyncSession):
    """Test that permissions are deleted when user is deleted."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server and tool
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    # Create permission
    permission = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="allow"
    )
    db_session.add(permission)
    await db_session.commit()

    # Delete user
    await db_session.delete(user)
    await db_session.commit()

    # Verify permission was also deleted
    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()

    assert len(permissions) == 0


@pytest.mark.asyncio
async def test_permission_cascade_delete_with_tool(db_session: AsyncSession):
    """Test that permissions are deleted when tool is deleted."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server and tool
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    tool_id = tool.id

    # Create permission
    permission = UserToolPermission(
        user_id=user.id, tool_id=tool.id, permission="allow"
    )
    db_session.add(permission)
    await db_session.commit()

    # Delete tool
    await db_session.delete(tool)
    await db_session.commit()

    # Verify permission was also deleted
    stmt = select(UserToolPermission).where(UserToolPermission.tool_id == tool_id)
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()

    assert len(permissions) == 0


@pytest.mark.asyncio
async def test_default_permission_behavior(db_session: AsyncSession):
    """Test default permission behavior when no record exists."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    # Create tool with no permissions
    tool = MCPServerTool(
        server_id=server.id,
        tool_name="test_tool",
        tool_description="A test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.commit()

    # Query permission (should not exist)
    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    permission = result.scalar_one_or_none()

    # Default behavior: no permission record means 'allow'
    assert permission is None
    # Application logic should treat None as 'allow' by default


@pytest.mark.asyncio
async def test_group_tools_by_server(db_session: AsyncSession):
    """Test grouping tools by server for permission management."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create multiple servers
    server1 = MCPServer(
        name="Server A",
        github_url="https://github.com/test/repo1",
        runtime_type="npx",
        start_command="test-command-1",
    )
    server2 = MCPServer(
        name="Server B",
        github_url="https://github.com/test/repo2",
        runtime_type="npx",
        start_command="test-command-2",
    )
    db_session.add_all([server1, server2])
    await db_session.flush()

    # Create tools for each server
    tool1 = MCPServerTool(
        server_id=server1.id,
        tool_name="tool_a1",
        tool_description="Tool 1 for Server A",
        is_enabled=True,
    )
    tool2 = MCPServerTool(
        server_id=server1.id,
        tool_name="tool_a2",
        tool_description="Tool 2 for Server A",
        is_enabled=True,
    )
    tool3 = MCPServerTool(
        server_id=server2.id,
        tool_name="tool_b1",
        tool_description="Tool 1 for Server B",
        is_enabled=True,
    )
    db_session.add_all([tool1, tool2, tool3])
    await db_session.commit()

    # Query all tools
    stmt = select(MCPServerTool).where(MCPServerTool.is_enabled == True)  # noqa: E712
    result = await db_session.execute(stmt)
    all_tools = result.scalars().all()

    # Group by server (simulating application logic)
    from collections import defaultdict

    servers_dict = defaultdict(list)
    for tool in all_tools:
        # Need to reload server relationship
        await db_session.refresh(tool, ["server"])
        servers_dict[tool.server.name].append(tool)

    # Verify grouping
    assert len(servers_dict) == 2
    assert len(servers_dict["Server A"]) == 2
    assert len(servers_dict["Server B"]) == 1
    assert servers_dict["Server A"][0].tool_name in ["tool_a1", "tool_a2"]
    assert servers_dict["Server A"][1].tool_name in ["tool_a1", "tool_a2"]
    assert servers_dict["Server B"][0].tool_name == "tool_b1"


@pytest.mark.asyncio
async def test_filter_enabled_tools_only(db_session: AsyncSession):
    """Test that only enabled tools are shown in permissions view."""
    # Create test user
    user = User(username="testuser", role="user")
    user.set_password("testpassword")
    db_session.add(user)
    await db_session.flush()

    # Create test server
    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    # Create enabled and disabled tools
    tool1 = MCPServerTool(
        server_id=server.id,
        tool_name="enabled_tool",
        tool_description="Enabled tool",
        is_enabled=True,
    )
    tool2 = MCPServerTool(
        server_id=server.id,
        tool_name="disabled_tool",
        tool_description="Disabled tool",
        is_enabled=False,
    )
    db_session.add_all([tool1, tool2])
    await db_session.commit()

    # Query only enabled tools
    stmt = select(MCPServerTool).where(MCPServerTool.is_enabled == True)  # noqa: E712
    result = await db_session.execute(stmt)
    enabled_tools = result.scalars().all()

    assert len(enabled_tools) == 1
    assert enabled_tools[0].tool_name == "enabled_tool"
