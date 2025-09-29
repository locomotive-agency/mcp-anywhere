from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.testclient import TestClient

from mcp_anywhere.web.middleware import MCPAuthMiddleware

@asynccontextmanager
async def mock_lifespan(app: Starlette):
    """Mock lifespan context manager for testing."""
    app.state.oauth_provider = MagicMock()
    yield

@pytest.mark.asyncio
async def test_mcp_auth_middleware_initialization(test_app_with_auth: Starlette):
    """
    Test that MCPAuthMiddleware can be initialized properly.
    """
    middleware = MCPAuthMiddleware(test_app_with_auth)
    assert isinstance(middleware, MCPAuthMiddleware)

@pytest_asyncio.fixture
async def valid_token():
    return "9d0bffa627e9db7ea78c11626fad7c935ac8e34e1d26a813e860d80f20b677e4"

@pytest_asyncio.fixture
async def test_app_with_auth():
    """Create test app with MCP Auth middleware."""

    # Create app with MCP Auth middleware
    app = Starlette(
        middleware=[
            Middleware(
                MCPAuthMiddleware,
            )
        ],
    )

    return app

@pytest.mark.asyncio
async def test_mcp_auth_middleware_no_bearer_token(test_app_with_auth: Starlette):
    """Test that MCP Auth middleware blocks users without token."""
    with TestClient(test_app_with_auth) as client:
        response = client.get("/mcp/")
        assert response.status_code == 401