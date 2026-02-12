"""MCP SDK-based OAuth provider implementation.
Uses the MCP auth module for spec-compliant OAuth 2.0 flows with PKCE support.
"""

import secrets
import time
import urllib.parse
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationCodeT,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    RefreshToken,
    TokenError, construct_redirect_uri,
)
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.auth import OAuthToken
from pydantic import AnyHttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException
from starlette.requests import Request

from mcp_anywhere.auth.models import OAuth2Client
from mcp_anywhere.config import Config
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.web.settings_routes import get_setting

logger = get_logger(__name__)


class MCPAnywhereAuthProvider(OAuthAuthorizationServerProvider):
    """OAuth 2.0 provider that integrates MCP SDK auth with our database with PKCE support."""

    def __init__(
        self, db_session_factory: Callable[[], Awaitable[AsyncSession]]
    ) -> None:
        """Initialize with a database session factory."""
        self.db_session_factory = db_session_factory
        self.auth_codes = {}  # In-memory storage for demo, use DB in production
        self.access_tokens = {}  # Token storage
        # Add in-memory client cache for immediate availability (single-user system)
        self.client_cache: dict[str, OAuthClientInformationFull] = {}
        # Storage for OAuth requests during authorization flow
        self.oauth_requests: dict[str, dict[str, Any]] = {}
        # Map access tokens to user IDs for user-specific filtering
        self.token_users: dict[str, str] = {}

    async def create_authorization_code(
        self,
        request: Request,
        client_id: str,
        redirect_uri: str,
        user_id: str,
        code_challenge: str = None,
        code_challenge_method: str = None,
        scopes: list[str] = None,
        scope: str = None,
        **kwargs,  # Accept any additional parameters
    ) -> str:
        """Generate and store an authorization code with PKCE support.

        Args:
            request: The HTTP request
            client_id: OAuth client ID
            redirect_uri: Redirect URI for the code
            user_id: ID of the authenticated user
            code_challenge: PKCE code challenge (optional)
            code_challenge_method: PKCE challenge method (optional)
            scopes: List of requested scopes (optional)
            scope: Legacy scope parameter (optional)
            **kwargs: Any additional OAuth parameters

        Returns:
            Generated authorization code
        """
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + 600  # 10 minutes

        # Handle scope/scopes parameter
        if scopes:
            scope_str = " ".join(scopes) if isinstance(scopes, list) else scopes
        elif scope:
            scope_str = scope
        else:
            scope_str = "mcp:read"

        self.auth_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope_str,
            "user_id": user_id,
            "expires_at": expires_at,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }

        logger.info(f"Created authorization code for client {client_id}")
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCodeT
    ) -> OAuthToken:
        """Exchange authorization code for access token with PKCE support.

        Note: Client authentication is already handled by the vendor's ClientAuthenticator
        before this method is called, so we don't need to re-validate credentials here.
        """
        # Extract the code string from the AuthorizationCode object
        code_string = authorization_code.code

        # Validate authorization code
        auth_code_data = self.auth_codes.get(code_string)
        if not auth_code_data:
            raise TokenError("invalid_grant")

        # Check expiration
        if time.time() > auth_code_data["expires_at"]:
            del self.auth_codes[code_string]
            raise TokenError("invalid_grant")

        # Validate code parameters
        if auth_code_data["client_id"] != client.client_id or auth_code_data[
            "redirect_uri"
        ] != str(client.redirect_uris[0]):
            raise TokenError("invalid_grant")

        # Note: PKCE verification is handled by the MCP SDK token handler before calling this method
        # The MCP SDK validates the code_verifier against the code_challenge before getting here
        # So we don't need to do PKCE validation again in the provider

        # Generate access token
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time() + 3600)  # 1 hour

        access_token = AccessToken(
            token=token,
            client_id=client.client_id,
            scopes=auth_code_data["scope"].split(),
            expires_at=expires_at,
            resource=f"{Config.SERVER_URL}{Config.MCP_PATH_PREFIX}",
        )

        # Store token for introspection
        self.access_tokens[token] = access_token

        # Store user_id mapping for this token
        self.token_users[token] = auth_code_data["user_id"]

        # Delete used authorization code
        del self.auth_codes[code_string]

        # Return OAuthToken for MCP SDK compatibility
        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(access_token.scopes),
        )

    async def introspect_token(self, token: str) -> AccessToken | None:
        """Introspect an access token for resource server validation.
        Required for the introspection endpoint.
        """
        access_token = self.access_tokens.get(token)

        if not access_token:
            return None

        # Check expiration
        if time.time() > access_token.expires_at:
            del self.access_tokens[token]
            # Clean up user mapping
            if token in self.token_users:
                del self.token_users[token]
            return None

        return access_token

    async def revoke_token(
        self, token: str, token_type_hint: str | None = None
    ) -> bool:
        """Revoke an access token."""
        if token in self.access_tokens:
            del self.access_tokens[token]
            # Clean up user mapping
            if token in self.token_users:
                del self.token_users[token]
            return True
        return False

    def get_user_id_from_token(self, token: str) -> str | None:
        """Get the user_id associated with an access token.

        Args:
            token: The access token string

        Returns:
            The user_id if found, None otherwise
        """
        return self.token_users.get(token)

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Get OAuth client information by client ID.

        This method is required by the MCP SDK for client validation.
        First checks in-memory cache, then database for single-user efficiency.

        Args:
            client_id: The OAuth client ID to lookup

        Returns:
            OAuthClientInformationFull object if found, None otherwise
        """
        # First check in-memory cache for immediate availability
        if client_id in self.client_cache:
            logger.debug(f"Client found in cache: {client_id}")
            return self.client_cache[client_id]

        # Then check database
        async with self.db_session_factory() as session:
            stmt = select(OAuth2Client).where(OAuth2Client.client_id == client_id)
            db_client = await session.scalar(stmt)

            if not db_client:
                logger.debug(f"Client not found in database: {client_id}")
                return None

            # Convert database model to MCP SDK model and cache it
            client_info = OAuthClientInformationFull(
                client_id=db_client.client_id,
                client_secret=(
                    db_client.client_secret if db_client.is_confidential else None
                ),
                client_name=db_client.client_name,
                redirect_uris=[db_client.redirect_uri],
                grant_types=["authorization_code"],
                response_types=["code"],
                scope=db_client.scope,
            )

            # Cache for future requests
            self.client_cache[client_id] = client_info
            logger.debug(f"Client loaded from database and cached: {client_id}")
            return client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Handle authorization request by storing OAuth parameters and redirecting.

        This method is called by the MCP SDK's /authorize endpoint.
        We need to store the OAuth request parameters so our consent page can access them.

        Args:
            client: The OAuth client requesting authorization
            params: Authorization parameters from the request

        Returns:
            URL to redirect the client to (login or consent page)
        """
        logger.info(f"Authorization request for client {client.client_id}")

        # Generate a state parameter for this OAuth request
        state = params.state or secrets.token_hex(16)

        # Store OAuth request parameters for later retrieval by consent page
        # Using the same pattern as simple auth but adapted for our session-based approach
        self.oauth_requests[state] = {
            "client_id": client.client_id,
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "scopes": params.scopes,
            "resource": params.resource,
            "state": params.state,  # Original state from client
        }

        # Build the consent URL with state parameter so consent page can retrieve OAuth data
        base_url = str(Config.SERVER_URL).rstrip("/")
        consent_url = f"{base_url}/auth/consent?state={state}"

        logger.info(f"Stored OAuth request with state {state}, redirecting to consent")
        return consent_url

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        """Load authorization code data.

        The MCP SDK calls this with client and code parameters.

        Args:
            client: The OAuth client information
            authorization_code: The authorization code to look up

        Returns:
            AuthorizationCode object if found and valid, None otherwise
        """
        auth_code_data = self.auth_codes.get(authorization_code)
        if not auth_code_data:
            return None

        # Convert dict to AuthorizationCode object for MCP SDK
        from pydantic import AnyHttpUrl

        return AuthorizationCode(
            code=authorization_code,
            client_id=auth_code_data["client_id"],
            redirect_uri=AnyHttpUrl(auth_code_data["redirect_uri"]),
            redirect_uri_provided_explicitly=True,
            expires_at=auth_code_data["expires_at"],
            scopes=auth_code_data["scope"].split() if auth_code_data["scope"] else [],
            code_challenge=auth_code_data.get("code_challenge"),
            resource=None,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load access token for introspection.

        Args:
            token: The access token to look up

        Returns:
            AccessToken object if found and valid, None otherwise
        """
        return await self.introspect_token(token)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        """Load refresh token.

        Args:
            client: The OAuth client
            refresh_token: The refresh token to look up

        Returns:
            RefreshToken object if found, None otherwise
        """
        # We don't currently support refresh tokens in this implementation
        return None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken
    ) -> AccessToken:
        """Exchange refresh token for new access token.

        Args:
            client: The OAuth client
            refresh_token: The refresh token to exchange

        Returns:
            New AccessToken

        Raises:
            TokenError: If refresh token is invalid
        """
        # We don't currently support refresh tokens in this implementation
        raise TokenError("unsupported_grant_type")

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Register a new OAuth client.

        The MCP SDK generates the client_id and passes it in client_info.
        We must use the provided client_id, not generate our own.
        For single-user systems, cache immediately for availability.

        Args:
            client_info: Complete client information including client_id generated by MCP SDK
        """
        logger.info(f"Registering OAuth client: {client_info.client_id}")

        # Cache immediately for MCP SDK availability (single-user system)
        self.client_cache[client_info.client_id] = client_info

        # Also persist to database
        client_id = client_info.client_id
        client_secret = client_info.client_secret  # Keep None for public clients
        client_name = client_info.client_name or "Unknown Client"
        redirect_uris = [str(url) for url in (client_info.redirect_uris or [])]
        scope = client_info.scope or "mcp:read mcp:write"

        # Determine if client is confidential (has a secret)
        is_confidential = client_secret is not None

        async with self.db_session_factory() as session:
            client = OAuth2Client(
                client_id=client_id,
                client_secret=client_secret,
                client_name=client_name,
                redirect_uri=redirect_uris[0] if redirect_uris else "",
                scope=scope,
                is_confidential=is_confidential,
            )
            session.add(client)
            await session.commit()
            logger.info(f"Successfully registered and cached client {client_id}")


class GoogleOAuthProvider(OAuthAuthorizationServerProvider):
    """Simple Google OAuth provider with essential functionality."""

    def __init__(self, db_session_factory: Callable[[], Awaitable[AsyncSession]]):
        self.db_session_factory = db_session_factory
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.state_mapping: dict[str, dict[str, str]] = {}
        self.g_token_mapping: dict[str, str] = {}
        self.state_resource_tokens: dict[str] = {}
        # Map access tokens to user IDs for user-specific filtering
        self.token_users: dict[str, str] = {}
        # Map authorization codes to user profiles for user lookup and creation
        self.code_user_profiles: dict[str, dict[str, Any]] = {}
        self.google_cache: dict[str, dict[str, Any]] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Get OAuth client information."""
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        """Register a new Google OAuth client.

        Args:
            client_info: Complete client information including client_id from env.
        """

        logger.info(f"Registering Google OAuth client: {client_info.client_id}")

        self.clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Generate an authorization URL for Google OAuth flow."""

        state = params.state or secrets.token_hex(16)

        logger.debug(f"Generate authorization params: {params}")

        # Handle scope/scopes parameter
        if params.scopes:
            scope_str = " ".join(params.scopes) if isinstance(params.scopes, list) else params.scopes
        elif params.scope:
            scope_str = params.scope
        else:
            scope_str = "mcp:read"

        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
            "client_id": client.client_id,
            "scope": scope_str,
        }

        auth_url = (
            f"{Config.GOOGLE_OAUTH_AUTH_URL}"
            f"?client_id={Config.GOOGLE_OAUTH_CLIENT_ID}"
            f"&redirect_uri={Config.SERVER_URL}{Config.GOOGLE_OAUTH_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={Config.GOOGLE_OAUTH_SCOPE}"
            f"&state={state}"
        )

        return auth_url

    async def build_auth_url(self) -> str:

        state = f"{secrets.token_hex(16)}_btn"

        redirect_uri = f"{Config.SERVER_URL}{Config.GOOGLE_OAUTH_REDIRECT_URI}"

        self.state_mapping[state] = {
            "redirect_uri": redirect_uri,
            "code_challenge": "code",
            "redirect_uri_provided_explicitly": "True",
            "client_id": f"{Config.GOOGLE_OAUTH_CLIENT_ID}",
            "scope": f"{Config.GOOGLE_OAUTH_SCOPE}"
        }

        auth_url = (
            f"{Config.GOOGLE_OAUTH_AUTH_URL}"
            f"?client_id={Config.GOOGLE_OAUTH_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={Config.GOOGLE_OAUTH_SCOPE}"
            f"&state={state}"
        )

        logger.debug(f"Building auth url: {auth_url}")

        return auth_url


    async def handle_callback(self, code: str, state: str) -> str:
        """Handle Google OAuth callback."""

        state_data = self.state_mapping.get(state)

        if not state_data:
            raise HTTPException(400, "Invalid state parameter")

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        scope = state_data["scope"]

        """Fetch Google access token"""
        access_token_url = Config.GOOGLE_OAUTH_TOKEN_URL
        http_response = await create_mcp_http_client().post(
            access_token_url,
            data=urllib.parse.urlencode({
                "client_id": Config.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": Config.GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{Config.SERVER_URL}{Config.GOOGLE_OAUTH_REDIRECT_URI}",
                "grant_type": "authorization_code",
            }),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        logger.debug(
            f"Google authorization HTTP Response: {http_response.status_code}"
        )

        http_response.raise_for_status()

        access_response = http_response.json()

        token = access_response.get('access_token')

        logger.debug(f"Google access_token: {token[:10]}...")

        user_profile = await self.get_user_profile(token)

        if not await self.user_has_domain_authorization(user_profile["email"]):
            logger.error(f"User {user_profile['email']} not part of authorized domain.")
            raise HTTPException(401, f"User {user_profile['email']} not part of authorized domain.")

        self.state_resource_tokens[state] = token

        new_code = secrets.token_hex(16)

        auth_code = AuthorizationCode(
            code=new_code,
            client_id=client_id,
            redirect_uri=str(AnyHttpUrl(redirect_uri)),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=scope.split(),
            code_challenge=code_challenge,
        )

        self.auth_codes[new_code] = auth_code

        # Store user profile mapping for user lookup and creation during token exchange
        self.code_user_profiles[new_code] = user_profile

        self.tokens[token] = AccessToken(
            token=token,
            client_id=client_id,
            scopes=Config.GOOGLE_OAUTH_SCOPE.split(),
            expires_at=None,
            **access_response
        )

        del self.state_mapping[state]

        return construct_redirect_uri(redirect_uri, code=new_code, state=state)

    async def load_authorization_code(
            self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        """Load an authorization code."""
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
            self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Exchange authorization code for tokens."""
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Invalid authorization code")

        mcp_token = secrets.token_hex(32)

        self.tokens[mcp_token] = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 3600,
        )

        google_token = next(
            (
                token
                for token, data in self.tokens.items()
                if (not token.startswith("mcp_")) and data.client_id == client.client_id
            ),
            None,
        )

        if google_token:
            self.g_token_mapping[mcp_token] = google_token

        # Look up user profile from authorization code
        user_profile = self.code_user_profiles.get(authorization_code.code)
        if user_profile:
            email = user_profile.get("email")
            given_name = user_profile.get("given_name", email.split("@")[0] if email else "User")
            
            # Query database for existing user or create new one
            session = await self.db_session_factory()
            async with session:
                from mcp_anywhere.auth.models import User
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                # Create user if doesn't exist
                if not user:
                    logger.info(f"Creating new user for email: {email}")
                    user = User(
                        username=email,
                        email=email,
                        password_hash="",  # Google OAuth users don't need password
                        type=Config.USER_GOOGLE,
                        role=Config.USER_ROLE
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    logger.info(f"Created new user with id: {user.id}")
                
                # Map token to user_id
                self.token_users[mcp_token] = str(user.id)
                logger.debug(f"Mapped MCP token to user_id: {user.id}")
            
            # Clean up user profile mapping
            del self.code_user_profiles[authorization_code.code]

        logger.debug(f"Providing authorization code to OAuth user: {mcp_token[:10]}...")

        del self.auth_codes[authorization_code.code]

        return OAuthToken(
            access_token=mcp_token,
            token_type="bearer",
            expires_in=3600,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate an access token."""
        access_token = self.tokens.get(token)
        if not access_token:
            return None

        # Check if expired
        if access_token.expires_at and access_token.expires_at < time.time():
            del self.tokens[token]
            # Clean up user mapping
            if token in self.token_users:
                del self.token_users[token]
            return None

        return access_token

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        """Load a refresh token - not supported."""
        return None

    async def exchange_refresh_token(
            self,
            client: OAuthClientInformationFull,
            refresh_token: RefreshToken,
            scopes: list[str],
    ) -> OAuthToken:
        """Exchange refresh token"""
        raise NotImplementedError("Not supported")

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        """Revoke a token."""
        if token in self.tokens:
            del self.tokens[token]
            # Clean up user mapping
            if token in self.token_users:
                del self.token_users[token]

    async def introspect_token(self, token: str) -> AccessToken | None:
        """Introspect an access token for resource server validation.
        Required for the introspection endpoint.
        """

        logger.debug(f"Introspecting token: {token[:10]}...")

        access_token = self.tokens.get(token)

        if not access_token:
            return None

        # Check expiration
        if time.time() > access_token.expires_at:
            del self.tokens[token]
            # Clean up user mapping
            if token in self.token_users:
                del self.token_users[token]
            return None

        return access_token

    def get_user_id_from_token(self, token: str) -> str | None:
        """Get the user_id associated with an access token.

        Args:
            token: The access token string

        Returns:
            The user_id if found, None otherwise
        """
        return self.token_users.get(token)

    async def get_user_profile(self, g_token: str) -> dict[str, Any]:

        if g_token in self.google_cache:
            logger.debug("Google profile from cache")
            return self.google_cache[g_token]

        logger.debug("Fetching Google profile")

        http_response = await create_mcp_http_client().get(
            Config.GOOGLE_OAUTH_USERINFO_URL,
            headers={"Authorization": f"Bearer {g_token}"}
        )

        if http_response.status_code != 200:
            logger.error(f"Google API error: {http_response.text}")
            raise HTTPException(
                status_code=http_response.status_code,
                detail="Failed to fetch Google OAuth user profile"
            )

        logger.debug(f"google user {http_response.json()["email"]}")

        self.google_cache[g_token] = http_response.json()

        return http_response.json()

    async def user_has_domain_authorization(self, email: str) -> bool:

        logger.debug(f"Checking if {email} matches allowed domain restriction")

        allowed_domain = await get_setting("oauth_user_allowed_domain")

        if allowed_domain is None:
            return True

        domain = email.split("@")[1]

        if domain == allowed_domain:
            return True

        return False

    async def get_google_token_for_token(self, token: str) -> str:
        return self.g_token_mapping[token]

    async def resource_token_from_state(self, state: str) -> str:
        logger.debug(f"Fetching resource token from state {state}")
        return self.state_resource_tokens[state]