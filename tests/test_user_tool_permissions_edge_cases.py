import time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_anywhere.auth.models import User, UserToolPermission
from mcp_anywhere.database import MCPServer, MCPServerTool


@pytest.mark.asyncio
async def test_delete_user_with_many_permissions(db_session: AsyncSession):
    """Test that deleting a user with hundreds of permissions works efficiently."""
    # Create test user
    user = User(username="poweruser", role="admin")
    user.set_password("testpass")
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

    tools = []
    for i in range(100):
        tool = MCPServerTool(
            server_id=server.id,
            tool_name=f"tool_{i}",
            tool_description=f"Test tool {i}",
            is_enabled=True,
        )
        tools.append(tool)
    db_session.add_all(tools)
    await db_session.flush()

    permissions = []
    for tool in tools:
        perm = UserToolPermission(
            user_id=user.id,
            tool_id=tool.id,
            permission="allow" if int(tool.tool_name.split("_")[1]) % 2 == 0 else "deny",
        )
        permissions.append(perm)
    db_session.add_all(permissions)
    await db_session.commit()

    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    existing_perms = result.scalars().all()
    assert len(existing_perms) == 100

    start_time = time.time()
    await db_session.delete(user)
    await db_session.commit()
    delete_duration = time.time() - start_time

    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    remaining_perms = result.scalars().all()

    assert len(remaining_perms) == 0, "All permissions should be deleted with user"

    # Performance check - warn if slow but don't fail (CI environments may be slower)
    if delete_duration >= 5.0:
        import warnings
        warnings.warn(
            f"Delete operation took {delete_duration:.2f}s, which is slower than expected. "
            f"This may indicate a performance issue, but could also be due to CI environment load.",
            UserWarning
        )

    stmt = select(MCPServerTool).where(MCPServerTool.server_id == server.id)
    result = await db_session.execute(stmt)
    remaining_tools = result.scalars().all()
    assert len(remaining_tools) == 100, "Tools should not be affected by user deletion"


@pytest.mark.asyncio
async def test_permission_isolation_between_users(db_session: AsyncSession):
    """Ensure that updating one user's permission does not affect another user's permission on the same tool."""
    user1 = User(username="user1", role="user")
    user1.set_password("pass1")
    user2 = User(username="user2", role="user")
    user2.set_password("pass2")
    db_session.add_all([user1, user2])
    await db_session.flush()

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
        tool_name="shared_tool",
        tool_description="Tool used by both users",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    perm1 = UserToolPermission(user_id=user1.id, tool_id=tool.id, permission="allow")
    perm2 = UserToolPermission(user_id=user2.id, tool_id=tool.id, permission="allow")
    db_session.add_all([perm1, perm2])
    await db_session.commit()

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user1.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    user1_perm = result.scalar_one()
    user1_perm.permission = "deny"
    await db_session.commit()

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user2.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    user2_perm = result.scalar_one()

    assert user1_perm.permission == "deny", "User1 permission should be deny"
    assert user2_perm.permission == "allow", "User2 permission should remain allow"


@pytest.mark.asyncio
async def test_delete_tool_with_many_user_permissions(db_session: AsyncSession):
    """Ensure deleting a tool cascades to its user permissions but does not delete users."""
    users = []
    for i in range(50):
        user = User(username=f"user_{i}", role="user")
        user.set_password("testpass")
        users.append(user)
    db_session.add_all(users)
    await db_session.flush()

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
        tool_name="popular_tool",
        tool_description="Tool with many users",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    tool_id = tool.id

    permissions = []
    for user in users:
        perm = UserToolPermission(
            user_id=user.id, tool_id=tool.id, permission="allow"
        )
        permissions.append(perm)
    db_session.add_all(permissions)
    await db_session.commit()

    stmt = select(UserToolPermission).where(UserToolPermission.tool_id == tool_id)
    result = await db_session.execute(stmt)
    existing_perms = result.scalars().all()
    assert len(existing_perms) == 50

    await db_session.delete(tool)
    await db_session.commit()

    stmt = select(UserToolPermission).where(UserToolPermission.tool_id == tool_id)
    result = await db_session.execute(stmt)
    remaining_perms = result.scalars().all()

    assert len(remaining_perms) == 0, "All permissions should be deleted with tool"

    stmt = select(User)
    result = await db_session.execute(stmt)
    remaining_users = result.scalars().all()
    assert len(remaining_users) == 50, "Users should not be affected by tool deletion"


@pytest.mark.asyncio
async def test_cannot_create_duplicate_permissions(db_session: AsyncSession):
    """Ensure duplicate UserToolPermission entries for the same user and tool are rejected and the original permission is preserved."""
    user = User(username="testuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.flush()

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
        tool_description="Test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    user_id = user.id
    tool_id = tool.id

    perm1 = UserToolPermission(user_id=user_id, tool_id=tool_id, permission="allow")
    db_session.add(perm1)
    await db_session.commit()

    perm2 = UserToolPermission(user_id=user_id, tool_id=tool_id, permission="deny")
    db_session.add(perm2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user_id, UserToolPermission.tool_id == tool_id
    )
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()
    assert len(permissions) == 1, "Only one permission should exist"
    assert permissions[0].permission == "allow", "Original permission should be preserved"


@pytest.mark.asyncio
async def test_bulk_permission_toggle(db_session: AsyncSession):
    """Test bulk toggling of many user tool permissions and ensure it remains performant."""

    user = User(username="bulkuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.flush()

    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    tools = []
    for i in range(100):
        tool = MCPServerTool(
            server_id=server.id,
            tool_name=f"tool_{i}",
            tool_description=f"Test tool {i}",
            is_enabled=True,
        )
        tools.append(tool)
    db_session.add_all(tools)
    await db_session.flush()

    permissions = []
    for tool in tools:
        perm = UserToolPermission(
            user_id=user.id, tool_id=tool.id, permission="allow"
        )
        permissions.append(perm)
    db_session.add_all(permissions)
    await db_session.commit()

    start_time = time.time()
    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    all_perms = result.scalars().all()

    for perm in all_perms:
        perm.permission = "deny"

    await db_session.commit()
    toggle_duration = time.time() - start_time

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.permission == "deny"
    )
    result = await db_session.execute(stmt)
    denied_perms = result.scalars().all()

    assert len(denied_perms) == 100, "All permissions should be updated to deny"

    # Performance check - warn if slow but don't fail (CI environments may be slower)
    if toggle_duration >= 10.0:
        import warnings
        warnings.warn(
            f"Bulk toggle operation took {toggle_duration:.2f}s, which is slower than expected. "
            f"This may indicate a performance issue, but could also be due to CI environment load.",
            UserWarning
        )


@pytest.mark.asyncio
async def test_query_permissions_for_nonexistent_user(db_session: AsyncSession):
    """Querying permissions for a nonexistent user should return an empty result set."""
    fake_user_id = "nonexistent-user-id"
    stmt = select(UserToolPermission).where(UserToolPermission.user_id == fake_user_id)
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()

    assert permissions == [], "Should return empty list for non-existent user"
    assert len(permissions) == 0, "Permission count should be 0"


@pytest.mark.asyncio
async def test_permission_for_disabled_tool(db_session: AsyncSession):
    """Ensure disabling a tool does not remove or alter existing permissions and they remain queryable."""
    user = User(username="testuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.flush()

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
        tool_description="Test tool",
        is_enabled=True,
    )
    db_session.add(tool)
    await db_session.flush()

    perm = UserToolPermission(user_id=user.id, tool_id=tool.id, permission="allow")
    db_session.add(perm)
    await db_session.commit()

    tool.is_enabled = False
    await db_session.commit()

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.tool_id == tool.id
    )
    result = await db_session.execute(stmt)
    existing_perm = result.scalar_one()

    assert existing_perm is not None, "Permission should still exist"
    assert existing_perm.permission == "allow", "Permission value should be unchanged"

    stmt = (
        select(MCPServerTool, UserToolPermission)
        .join(UserToolPermission)
        .where(UserToolPermission.user_id == user.id)
    )
    result = await db_session.execute(stmt)
    tool_perm_pairs = result.all()

    assert len(tool_perm_pairs) == 1, "Should find the tool-permission pair"
    found_tool, found_perm = tool_perm_pairs[0]
    assert found_tool.is_enabled is False, "Tool should be disabled"
    assert found_perm.permission == "allow", "Permission should still be allow"


@pytest.mark.asyncio
async def test_permissions_after_server_deletion(db_session: AsyncSession):
    """Ensure deleting a server cascade-deletes its tools and permissions but preserves the user."""
    user = User(username="testuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.flush()

    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    server_id = server.id

    tools = []
    for i in range(5):
        tool = MCPServerTool(
            server_id=server.id,
            tool_name=f"tool_{i}",
            tool_description=f"Test tool {i}",
            is_enabled=True,
        )
        tools.append(tool)
    db_session.add_all(tools)
    await db_session.flush()

    permissions = []
    for tool in tools:
        perm = UserToolPermission(
            user_id=user.id, tool_id=tool.id, permission="allow"
        )
        permissions.append(perm)
    db_session.add_all(permissions)
    await db_session.commit()

    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    existing_perms = result.scalars().all()
    assert len(existing_perms) == 5

    await db_session.delete(server)
    await db_session.commit()

    stmt = select(MCPServerTool).where(MCPServerTool.server_id == server_id)
    result = await db_session.execute(stmt)
    remaining_tools = result.scalars().all()
    assert len(remaining_tools) == 0, "All tools should be cascade-deleted"

    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    remaining_perms = result.scalars().all()
    assert len(remaining_perms) == 0, "All permissions should be cascade-deleted"

    stmt = select(User).where(User.id == user.id)
    result = await db_session.execute(stmt)
    remaining_user = result.scalar_one()
    assert remaining_user is not None, "User should not be affected"


@pytest.mark.asyncio
async def test_user_with_no_permissions(db_session: AsyncSession):
    """Ensure a user with no permissions returns empty results for all permission and tool queries."""
    user = User(username="newuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.commit()

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
    assert len(allowed_tools) == 0, "Should have no allowed tools"

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
    assert len(denied_tools) == 0, "Should have no denied tools"

    stmt = select(UserToolPermission).where(UserToolPermission.user_id == user.id)
    result = await db_session.execute(stmt)
    all_perms = result.scalars().all()
    assert len(all_perms) == 0, "Should have no permissions at all"


@pytest.mark.asyncio
async def test_permission_counts_by_type(db_session: AsyncSession):
    """Verify that permission counts by type ('allow' and 'deny') are correct for a user with mixed permissions."""

    user = User(username="testuser", role="user")
    user.set_password("testpass")
    db_session.add(user)
    await db_session.flush()

    server = MCPServer(
        name="Test Server",
        github_url="https://github.com/test/repo",
        runtime_type="npx",
        start_command="test-command",
    )
    db_session.add(server)
    await db_session.flush()

    for i in range(10):
        tool = MCPServerTool(
            server_id=server.id,
            tool_name=f"tool_{i}",
            tool_description=f"Test tool {i}",
            is_enabled=True,
        )
        db_session.add(tool)
        await db_session.flush()

        perm = UserToolPermission(
            user_id=user.id,
            tool_id=tool.id,
            permission="allow" if i % 2 == 0 else "deny",
        )
        db_session.add(perm)

    await db_session.commit()

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.permission == "allow"
    )
    result = await db_session.execute(stmt)
    allowed_count = len(result.scalars().all())

    stmt = select(UserToolPermission).where(
        UserToolPermission.user_id == user.id, UserToolPermission.permission == "deny"
    )
    result = await db_session.execute(stmt)
    denied_count = len(result.scalars().all())

    assert allowed_count == 5, "Should have 5 allowed permissions"
    assert denied_count == 5, "Should have 5 denied permissions"
    assert allowed_count + denied_count == 10, "Total should be 10 permissions"
