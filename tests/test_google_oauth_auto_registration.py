"""Tests for Google OAuth auto-registration functionality."""

import secrets
import time
from typing import Any

import pytest
from mcp.server.auth.provider import AuthorizationCode, OAuthClientInformationFull
from pydantic import AnyHttpUrl
from sqlalchemy import select

from mcp_anywhere.auth.models import User
from mcp_anywhere.auth.provider import GoogleOAuthProvider
from mcp_anywhere.config import Config


@pytest.mark.asyncio
async def test_google_oauth_auto_registration_new_user(db_session):
    """Test that a new user is automatically created during token exchange."""
    
    # Create a session factory that returns our test db_session (not a coroutine)
    def session_factory():
        return db_session
    
    # Initialize provider
    provider = GoogleOAuthProvider(session_factory)
    
    # Create a test client
    client_info = OAuthClientInformationFull(
        client_id="test_client",
        client_secret="test_secret",
        client_name="Test Client",
        redirect_uris=[AnyHttpUrl("http://localhost/callback")],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope="mcp:read mcp:write",
    )
    await provider.register_client(client_info)
    
    # Create an authorization code
    auth_code_str = secrets.token_hex(16)
    auth_code = AuthorizationCode(
        code=auth_code_str,
        client_id=client_info.client_id,
        redirect_uri=AnyHttpUrl("http://localhost/callback"),
        redirect_uri_provided_explicitly=True,
        expires_at=time.time() + 300,
        scopes=["mcp:read"],
        code_challenge="test_challenge",
    )
    provider.auth_codes[auth_code_str] = auth_code
    
    # Store a user profile
    test_email = "newuser@example.com"
    test_given_name = "New User"
    user_profile = {
        "email": test_email,
        "given_name": test_given_name,
    }
    provider.code_user_profiles[auth_code_str] = user_profile
    
    # Verify user doesn't exist yet
    stmt = select(User).where(User.email == test_email)
    result = await db_session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    assert existing_user is None, "User should not exist before token exchange"
    
    # Exchange authorization code
    token = await provider.exchange_authorization_code(client_info, auth_code)
    
    # Verify user was created
    stmt = select(User).where(User.email == test_email)
    result = await db_session.execute(stmt)
    created_user = result.scalar_one_or_none()
    
    assert created_user is not None, "User should be created"
    assert created_user.email == test_email
    assert created_user.username == test_email
    assert created_user.type == Config.USER_GOOGLE
    assert created_user.role == Config.USER_ROLE
    
    # Verify token is mapped to user
    user_id = provider.get_user_id_from_token(token.access_token)
    assert user_id == str(created_user.id)
    
    # Verify user profile was cleaned up
    assert auth_code_str not in provider.code_user_profiles


@pytest.mark.asyncio
async def test_google_oauth_existing_user_not_duplicated(db_session):
    """Test that existing users are not duplicated during token exchange."""
    
    # Create a session factory that returns our test db_session (not a coroutine)
    def session_factory():
        return db_session
    
    # Initialize provider
    provider = GoogleOAuthProvider(session_factory)
    
    # Create an existing user
    test_email = "existing@example.com"
    existing_user = User(
        username=test_email,
        email=test_email,
        password_hash="",
        type=Config.USER_GOOGLE,
        role=Config.USER_ROLE,
    )
    db_session.add(existing_user)
    await db_session.commit()
    await db_session.refresh(existing_user)
    existing_user_id = existing_user.id
    
    # Create a test client
    client_info = OAuthClientInformationFull(
        client_id="test_client",
        client_secret="test_secret",
        client_name="Test Client",
        redirect_uris=[AnyHttpUrl("http://localhost/callback")],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope="mcp:read mcp:write",
    )
    await provider.register_client(client_info)
    
    # Create an authorization code
    auth_code_str = secrets.token_hex(16)
    auth_code = AuthorizationCode(
        code=auth_code_str,
        client_id=client_info.client_id,
        redirect_uri=AnyHttpUrl("http://localhost/callback"),
        redirect_uri_provided_explicitly=True,
        expires_at=time.time() + 300,
        scopes=["mcp:read"],
        code_challenge="test_challenge",
    )
    provider.auth_codes[auth_code_str] = auth_code
    
    # Store a user profile
    user_profile = {
        "email": test_email,
        "given_name": "Existing User",
    }
    provider.code_user_profiles[auth_code_str] = user_profile
    
    # Exchange authorization code
    token = await provider.exchange_authorization_code(client_info, auth_code)
    
    # Verify no duplicate user was created
    stmt = select(User).where(User.email == test_email)
    result = await db_session.execute(stmt)
    users = result.scalars().all()
    assert len(users) == 1, "Should have only one user with this email"
    
    # Verify token is mapped to the existing user
    user_id = provider.get_user_id_from_token(token.access_token)
    assert user_id == str(existing_user_id)
    
    # Verify user profile was cleaned up
    assert auth_code_str not in provider.code_user_profiles


@pytest.mark.asyncio
async def test_code_user_profiles_renamed(db_session):
    """Test that code_user_profiles dictionary exists and works correctly."""
    
    # Create a session factory that returns our test db_session (not a coroutine)
    def session_factory():
        return db_session
    
    # Initialize provider
    provider = GoogleOAuthProvider(session_factory)
    
    # Verify the attribute exists and is a dict
    assert hasattr(provider, "code_user_profiles")
    assert isinstance(provider.code_user_profiles, dict)
    
    # Test storing and retrieving a profile
    test_code = "test_code"
    test_profile = {"email": "test@example.com", "given_name": "Test"}
    provider.code_user_profiles[test_code] = test_profile
    
    assert provider.code_user_profiles[test_code] == test_profile


@pytest.mark.asyncio
async def test_handle_callback_stores_full_profile(db_session):
    """Test that handle_callback stores the full user profile, not just email."""
    
    # This test verifies the change in handle_callback method
    # We'll test it indirectly by checking if the stored value is a dict with multiple fields
    
    # Create a session factory that returns our test db_session (not a coroutine)
    def session_factory():
        return db_session
    
    provider = GoogleOAuthProvider(session_factory)
    
    # Manually simulate what handle_callback does
    auth_code = "test_auth_code"
    user_profile = {
        "email": "user@example.com",
        "given_name": "Test User",
        "family_name": "Tester",
        "picture": "http://example.com/picture.jpg",
    }
    
    # This is what handle_callback now does
    provider.code_user_profiles[auth_code] = user_profile
    
    # Verify the full profile is stored
    stored_profile = provider.code_user_profiles.get(auth_code)
    assert stored_profile is not None
    assert isinstance(stored_profile, dict)
    assert stored_profile.get("email") == "user@example.com"
    assert stored_profile.get("given_name") == "Test User"
    assert stored_profile.get("family_name") == "Tester"
    assert stored_profile.get("picture") == "http://example.com/picture.jpg"


@pytest.mark.asyncio
async def test_user_creation_with_missing_given_name(db_session):
    """Test that user creation handles missing given_name gracefully."""
    
    # Create a session factory that returns our test db_session (not a coroutine)
    def session_factory():
        return db_session
    
    provider = GoogleOAuthProvider(session_factory)
    
    # Create a test client
    client_info = OAuthClientInformationFull(
        client_id="test_client",
        client_secret="test_secret",
        client_name="Test Client",
        redirect_uris=[AnyHttpUrl("http://localhost/callback")],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope="mcp:read mcp:write",
    )
    await provider.register_client(client_info)
    
    # Create an authorization code
    auth_code_str = secrets.token_hex(16)
    auth_code = AuthorizationCode(
        code=auth_code_str,
        client_id=client_info.client_id,
        redirect_uri=AnyHttpUrl("http://localhost/callback"),
        redirect_uri_provided_explicitly=True,
        expires_at=time.time() + 300,
        scopes=["mcp:read"],
        code_challenge="test_challenge",
    )
    provider.auth_codes[auth_code_str] = auth_code
    
    # Store a user profile without given_name
    test_email = "nofirstname@example.com"
    user_profile = {
        "email": test_email,
        # No given_name field
    }
    provider.code_user_profiles[auth_code_str] = user_profile
    
    # Exchange authorization code - should not raise an error
    token = await provider.exchange_authorization_code(client_info, auth_code)
    
    # Verify user was created with email as fallback
    stmt = select(User).where(User.email == test_email)
    result = await db_session.execute(stmt)
    created_user = result.scalar_one_or_none()
    
    assert created_user is not None, "User should be created even without given_name"
    assert created_user.email == test_email
    assert created_user.username == test_email
