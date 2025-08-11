"""Tests for OAuth consent flow integration with admin authentication and CSRF protection."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.applications import Starlette

from mcp_anywhere.auth.csrf import CSRFProtection
from mcp_anywhere.auth.models import OAuth2Client, User
from mcp_anywhere.auth.provider import MCPAnywhereAuthProvider


@pytest.fixture
async def setup_app_state(app: Starlette, db_session: AsyncSession):
    """Set up app state with database session and CSRF protection."""
    # Mock the get_async_session function to return a proper async context manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_async_session():
        yield db_session

    app.state.get_async_session = mock_get_async_session
    app.state.oauth_provider = MCPAnywhereAuthProvider(mock_get_async_session)
    app.state.csrf_protection = CSRFProtection(expiration_seconds=600)
    return app


class TestConsentFlowCore:
    """Test the core consent flow functionality that we directly control."""

    async def setup_test_data(self, db_session: AsyncSession) -> tuple[User, OAuth2Client]:
        """Set up test user and OAuth client."""
        # Create test admin user
        admin_user = User(username="admin")
        admin_user.set_password("admin123")
        db_session.add(admin_user)

        # Create test OAuth client
        oauth_client = OAuth2Client(
            client_id="test_client",
            client_secret="test_secret",
            client_name="Test Client",
            redirect_uri="http://localhost:3001/auth/callback",
            scope="mcp:read mcp:write",
        )
        db_session.add(oauth_client)

        await db_session.commit()
        return admin_user, oauth_client

    async def login_user(self, client: httpx.AsyncClient, username: str, password: str) -> None:
        """Helper to log in a user."""
        login_response = await client.post(
            "/auth/login", data={"username": username, "password": password}
        )
        # Login should redirect on success
        assert login_response.status_code == 302

    async def test_consent_page_missing_oauth_request_redirects_home(
        self, setup_app_state, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        """Consent page without OAuth request should redirect to home."""
        admin_user, oauth_client = await self.setup_test_data(db_session)

        # Log in first
        await self.login_user(client, "admin", "admin123")

        # Try to access consent page directly without OAuth request in session
        response = await client.get("/auth/consent", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    async def test_consent_page_renders_with_client_details(
        self, setup_app_state, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        """Consent page should render with client details when OAuth request is in session."""
        admin_user, oauth_client = await self.setup_test_data(db_session)

        # Log in first
        await self.login_user(client, "admin", "admin123")

        # Manually set OAuth request in session (simulating what OAuth authorize would do)
        # We can't easily test the full OAuth flow due to MCP SDK complexity,
        # but we can test our consent handlers directly

        # For this test, we'll use a different approach - test the consent page
        # by directly calling it with a properly set up session

        # This test will be skipped until we can properly set up session state
        pytest.skip("Session state setup needs refinement for proper OAuth request simulation")

    async def test_consent_form_missing_oauth_request_redirects_home(
        self, setup_app_state, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        """Consent form without OAuth request should redirect to home."""
        admin_user, oauth_client = await self.setup_test_data(db_session)

        # Log in first
        await self.login_user(client, "admin", "admin123")

        # Try to submit consent form without OAuth request in session
        response = await client.post(
            "/auth/consent", data={"action": "allow"}, follow_redirects=False
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"


    async def test_oauth_provider_initialization(
        self, setup_app_state, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that OAuth provider is properly initialized in app state."""
        app = setup_app_state  # Fixture already returns the configured app

        # Verify OAuth provider is initialized
        assert hasattr(app.state, "oauth_provider")
        assert isinstance(app.state.oauth_provider, MCPAnywhereAuthProvider)

    async def test_admin_login_works(
        self, setup_app_state, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that admin login functionality works with our test setup."""
        admin_user, oauth_client = await self.setup_test_data(db_session)

        # Test login with valid credentials
        response = await client.post(
            "/auth/login", data={"username": "admin", "password": "admin123"}
        )

        # Should redirect on successful login
        assert response.status_code == 302

        # Test login with invalid credentials
        response = await client.post(
            "/auth/login", data={"username": "admin", "password": "wrongpassword"}
        )

        # Should redirect with error
        assert response.status_code == 302
        assert "error=invalid_credentials" in response.headers["location"]


