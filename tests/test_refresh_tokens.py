"""Tests for OAuth refresh token support in both auth providers."""

import secrets
import time

import pytest
from mcp.server.auth.provider import (
    AuthorizationCode,
    OAuthClientInformationFull,
    RefreshToken,
    TokenError,
)
from pydantic import AnyHttpUrl

from mcp_anywhere.auth.models import OAuth2Client
from mcp_anywhere.auth.provider import (
    SUPPORTED_GRANT_TYPES,
    GoogleOAuthProvider,
    MCPAnywhereAuthProvider,
)
from mcp_anywhere.config import Config

REDIRECT_URI = "http://localhost/callback"


def _make_client_info(client_id: str = "test_client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret="test_secret",
        client_name="Test Client",
        redirect_uris=[AnyHttpUrl(REDIRECT_URI)],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="mcp:read mcp:write",
    )


async def _authorize_and_exchange(provider, client_info, db_session=None):
    """Run the authorization-code part of the flow and return the token response."""
    code = await provider.create_authorization_code(
        request=None,
        client_id=client_info.client_id,
        redirect_uri=REDIRECT_URI,
        user_id="42",
        code_challenge="test_challenge",
        code_challenge_method="S256",
        scopes=["mcp:read"],
    )
    auth_code = await provider.load_authorization_code(client_info, code)
    return await provider.exchange_authorization_code(client_info, auth_code)


@pytest.mark.asyncio
async def test_exchange_authorization_code_returns_refresh_token(db_session):
    """Token response must include a refresh token alongside the access token."""

    def session_factory():
        return db_session

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    token = await _authorize_and_exchange(provider, client_info)

    assert token.access_token
    assert token.refresh_token, "Token response should include a refresh token"
    assert token.expires_in == Config.ACCESS_TOKEN_EXPIRES_IN

    # Refresh token is stored and bound to the client and user
    stored = provider.refresh_tokens[token.refresh_token]
    assert stored.client_id == client_info.client_id
    assert stored.scopes == ["mcp:read"]
    assert provider.refresh_token_users[token.refresh_token] == "42"


@pytest.mark.asyncio
async def test_load_refresh_token_validates_client_and_expiry(db_session):
    """load_refresh_token returns the token only for the issuing client."""

    def session_factory():
        return db_session

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    token = await _authorize_and_exchange(provider, client_info)

    # Valid lookup
    loaded = await provider.load_refresh_token(client_info, token.refresh_token)
    assert loaded is not None
    assert loaded.token == token.refresh_token

    # Unknown token
    assert await provider.load_refresh_token(client_info, "missing") is None

    # Wrong client
    other_client = _make_client_info(client_id="other_client")
    assert await provider.load_refresh_token(other_client, token.refresh_token) is None

    # Expired refresh token is dropped
    expired = RefreshToken(
        token="expired-token",
        client_id=client_info.client_id,
        scopes=["mcp:read"],
        expires_at=int(time.time()) - 10,
    )
    provider.refresh_tokens["expired-token"] = expired
    provider.refresh_token_users["expired-token"] = "42"
    assert await provider.load_refresh_token(client_info, "expired-token") is None
    assert "expired-token" not in provider.refresh_tokens
    assert "expired-token" not in provider.refresh_token_users


@pytest.mark.asyncio
async def test_exchange_refresh_token_rotates_and_preserves_user(db_session):
    """Refreshing returns a new token pair and invalidates the old refresh token."""

    def session_factory():
        return db_session

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    token = await _authorize_and_exchange(provider, client_info)
    old_refresh = token.refresh_token

    loaded = await provider.load_refresh_token(client_info, old_refresh)
    new_token = await provider.exchange_refresh_token(
        client_info, loaded, loaded.scopes
    )

    # New pair issued
    assert new_token.access_token != token.access_token
    assert new_token.refresh_token != old_refresh
    assert new_token.expires_in == Config.ACCESS_TOKEN_EXPIRES_IN

    # New access token is valid and keeps the user association
    access = await provider.load_access_token(new_token.access_token)
    assert access is not None
    assert provider.get_user_id_from_token(new_token.access_token) == "42"

    # Rotation: old refresh token no longer usable
    assert old_refresh not in provider.refresh_tokens
    assert await provider.load_refresh_token(client_info, old_refresh) is None
    with pytest.raises(TokenError):
        await provider.exchange_refresh_token(
            client_info,
            RefreshToken(
                token=old_refresh,
                client_id=client_info.client_id,
                scopes=["mcp:read"],
            ),
            ["mcp:read"],
        )


@pytest.mark.asyncio
async def test_revoke_token_handles_refresh_tokens(db_session):
    """Revocation endpoint should also revoke refresh tokens."""

    def session_factory():
        return db_session

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    token = await _authorize_and_exchange(provider, client_info)

    assert await provider.revoke_token(token.refresh_token) is True
    assert token.refresh_token not in provider.refresh_tokens
    assert await provider.load_refresh_token(client_info, token.refresh_token) is None

    # Access token revocation still works
    assert await provider.revoke_token(token.access_token) is True
    assert await provider.revoke_token("unknown-token") is False


@pytest.mark.asyncio
async def test_get_client_includes_refresh_token_grant(db_session):
    """Clients loaded from the database may use the refresh_token grant.

    The MCP SDK token handler rejects grants not listed in the client's
    grant_types, so get_client must include refresh_token for clients
    registered before refresh token support existed.
    """

    def session_factory():
        return db_session

    provider = MCPAnywhereAuthProvider(session_factory)

    # Simulate a client registered before refresh token support
    legacy = OAuth2Client(
        client_id="legacy_client",
        client_secret="secret",
        client_name="Legacy",
        redirect_uri=REDIRECT_URI,
        scope="mcp:read",
        grant_types="authorization_code",
    )
    db_session.add(legacy)
    await db_session.commit()

    client_info = await provider.get_client("legacy_client")
    assert client_info is not None
    assert "refresh_token" in client_info.grant_types

    # Newly registered clients persist their grant types
    new_client = _make_client_info(client_id="new_client")
    await provider.register_client(new_client)
    provider.client_cache.clear()  # force DB read
    reloaded = await provider.get_client("new_client")
    assert reloaded is not None
    assert set(SUPPORTED_GRANT_TYPES).issubset(set(reloaded.grant_types))


@pytest.mark.asyncio
async def test_token_lifetimes_use_config(db_session, monkeypatch):
    """Access and refresh token lifetimes come from configuration."""

    def session_factory():
        return db_session

    monkeypatch.setattr(Config, "ACCESS_TOKEN_EXPIRES_IN", 7200)
    monkeypatch.setattr(Config, "REFRESH_TOKEN_EXPIRES_IN", 86400)

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    before = int(time.time())
    token = await _authorize_and_exchange(provider, client_info)

    assert token.expires_in == 7200
    access = provider.access_tokens[token.access_token]
    assert before + 7200 <= access.expires_at <= int(time.time()) + 7200

    refresh = provider.refresh_tokens[token.refresh_token]
    assert before + 86400 <= refresh.expires_at <= int(time.time()) + 86400


@pytest.mark.asyncio
async def test_refresh_token_never_expires_when_configured(db_session, monkeypatch):
    """REFRESH_TOKEN_EXPIRES_IN=0 issues non-expiring refresh tokens."""

    def session_factory():
        return db_session

    monkeypatch.setattr(Config, "REFRESH_TOKEN_EXPIRES_IN", 0)

    provider = MCPAnywhereAuthProvider(session_factory)
    client_info = _make_client_info()
    provider.client_cache[client_info.client_id] = client_info

    token = await _authorize_and_exchange(provider, client_info)

    refresh = provider.refresh_tokens[token.refresh_token]
    assert refresh.expires_at is None
    assert await provider.load_refresh_token(client_info, token.refresh_token) is not None


@pytest.mark.asyncio
async def test_google_provider_issues_and_rotates_refresh_tokens(db_session):
    """Google provider issues refresh tokens and preserves user/Google mappings."""

    def session_factory():
        return db_session

    provider = GoogleOAuthProvider(session_factory)
    client_info = _make_client_info()
    await provider.register_client(client_info)

    # Authorization code with an auto-registered user profile
    auth_code_str = secrets.token_hex(16)
    auth_code = AuthorizationCode(
        code=auth_code_str,
        client_id=client_info.client_id,
        redirect_uri=AnyHttpUrl(REDIRECT_URI),
        redirect_uri_provided_explicitly=True,
        expires_at=time.time() + 300,
        scopes=["mcp:read"],
        code_challenge="test_challenge",
    )
    provider.auth_codes[auth_code_str] = auth_code
    provider.code_user_profiles[auth_code_str] = {
        "email": "refresh@example.com",
        "given_name": "Refresh",
    }

    token = await provider.exchange_authorization_code(client_info, auth_code)

    assert token.refresh_token, "Google provider should issue a refresh token"
    user_id = provider.get_user_id_from_token(token.access_token)
    assert user_id is not None
    assert provider.refresh_token_users[token.refresh_token] == user_id

    # Simulate the Google token mapping that handle_callback would create
    provider.refresh_token_g_tokens[token.refresh_token] = "google-token-123"

    loaded = await provider.load_refresh_token(client_info, token.refresh_token)
    assert loaded is not None

    new_token = await provider.exchange_refresh_token(
        client_info, loaded, loaded.scopes
    )

    # New pair issued; user and Google token mappings preserved
    assert new_token.access_token != token.access_token
    assert new_token.refresh_token != token.refresh_token
    assert provider.get_user_id_from_token(new_token.access_token) == user_id
    assert provider.g_token_mapping[new_token.access_token] == "google-token-123"
    assert (
        provider.refresh_token_g_tokens[new_token.refresh_token] == "google-token-123"
    )

    # Rotation: old refresh token invalidated
    assert token.refresh_token not in provider.refresh_tokens
    assert await provider.load_refresh_token(client_info, token.refresh_token) is None
    with pytest.raises(TokenError):
        await provider.exchange_refresh_token(client_info, loaded, loaded.scopes)


@pytest.mark.asyncio
async def test_google_introspect_token_handles_no_expiry(db_session):
    """Google resource tokens are stored without expiry and must not crash."""
    from mcp.server.auth.provider import AccessToken

    def session_factory():
        return db_session

    provider = GoogleOAuthProvider(session_factory)
    provider.tokens["google-raw-token"] = AccessToken(
        token="google-raw-token",
        client_id="test_client",
        scopes=["mcp:read"],
        expires_at=None,
    )

    result = await provider.introspect_token("google-raw-token")
    assert result is not None
    assert result.token == "google-raw-token"
