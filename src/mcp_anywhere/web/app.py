"""Simplified async Starlette application for MCP Anywhere."""

from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from mcp_anywhere.auth.initialization import initialize_oauth_data
from mcp_anywhere.auth.provider import MCPAnywhereAuthProvider, GoogleOAuthProvider
from mcp_anywhere.auth.routes import create_oauth_http_routes
from mcp_anywhere.config import Config
from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.core.mcp_manager import MCPManager
from mcp_anywhere.core.middleware import ToolFilterMiddleware
from mcp_anywhere.database import close_db, get_async_session, init_db
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.web import routes
from mcp_anywhere.web.config_routes import config_routes
from mcp_anywhere.web.middleware import (
    MCPAuthMiddleware,
    RedirectMiddleware,
    SessionAuthMiddleware,
)
from mcp_anywhere.web.secret_routes import secret_file_routes
from mcp_anywhere.web.settings_routes import settings_routes, initialize_default_settings
from mcp_anywhere.web.user_routes import routes as user_routes

logger = get_logger(__name__)


async def create_app(transport_mode: str = "http") -> Starlette:
    """Creates and configures the main Starlette application.

    This is a SIMPLIFIED version that:
    1. Creates everything upfront (like the old architecture)
    2. Uses a single, simple lifespan
    3. Passes FastMCP's lifespan directly to Starlette
    """
    # Initialize database first (outside lifespan for simplicity)
    await init_db()

    # Initialize OAuth data
    try:
        admin_user, oauth_client = await initialize_oauth_data()
        logger.info(
            f"OAuth initialized - Admin: {admin_user.username}, Client: {oauth_client.client_id}"
        )
    except Exception as e:
        logger.exception(f"Failed to initialize OAuth data: {e}")
        raise

    # Initialize default settings
    try:
        await initialize_default_settings()
        logger.info("Default settings initialized")
    except Exception as e:
        logger.exception(f"Failed to initialize default settings: {e}")
        raise

    # Create the MCP router (like old create_mcp_manager)
    router = FastMCP(
        name="MCP-Anywhere",
        instructions="""This router provides access to multiple MCP servers.
        
All tools from mounted servers are available directly with prefixed names.
You can use tools/list to see all available tools from all mounted servers.
""",
    )
    router.add_middleware(ToolFilterMiddleware())

    # Create MCP manager
    mcp_manager = MCPManager(router)

    # Initialize container manager and mount servers (skip during tests)
    import os

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        container_manager = ContainerManager()

        if Config.REBUILD_CONTAINERS_ON_STARTUP:
            logger.debug(f"Rebuilding containers on startup due to config: {Config.REBUILD_CONTAINERS_ON_STARTUP}")
            await container_manager.initialize_and_build_servers()

        await container_manager.mount_built_servers(mcp_manager)

    # Create FastMCP HTTP app (ONCE, like the old architecture)
    # The key insight from the old code: FastMCP creates its app with lifespan included
    mcp_http_app = mcp_manager.router.http_app(path="/", transport="http")

    oauth_provider = None

    if transport_mode == "http":
        oauth_provider = GoogleOAuthProvider(get_async_session) \
            if Config.GOOGLE_OAUTH_CLIENT_SECRET is not None else MCPAnywhereAuthProvider(get_async_session)

    # Configure middleware - Using SameSite cookies for CSRF protection (modern approach)
    middleware = [
        Middleware(
            SessionMiddleware,
            secret_key=Config.SECRET_KEY,
            max_age=Config.SESSION_MAX_AGE,
        ),
        Middleware(SessionAuthMiddleware),
    ]

    if transport_mode == "http":
        middleware.extend(
            [
                Middleware(RedirectMiddleware),
                Middleware(MCPAuthMiddleware),
            ]
        )

    # Create routes
    app_routes = []

    # Add OAuth routes if in HTTP mode
    if transport_mode == "http" and oauth_provider:
        oauth_routes = create_oauth_http_routes(get_async_session, oauth_provider)
        app_routes.extend(oauth_routes)

    # Add other routes
    app_routes.extend(
        [
            *config_routes,
            *secret_file_routes,
            *settings_routes,
            *user_routes,
            *routes.routes,
            # Static files mount
            Mount(
                "/static",
                app=StaticFiles(directory="src/mcp_anywhere/web/static"),
                name="static",
            ),
        ]
    )

    # Simple lifespan for database cleanup
    @asynccontextmanager
    async def simple_lifespan(app: Starlette):
        """Minimal lifespan for database cleanup."""
        yield
        await close_db()

    # Create the main app - THE KEY: Use FastMCP's lifespan, not our own!
    # This is what the old architecture did right (line 140 in asgi.py.bak)
    app = Starlette(
        debug=True,
        lifespan=mcp_http_app.lifespan if transport_mode == "http" else simple_lifespan,
        middleware=middleware,
        routes=app_routes,
    )

    # Mount the FastMCP app at /mcp (like old architecture)
    if transport_mode == "http":
        app.mount(Config.MCP_PATH_MOUNT, mcp_http_app)

    # Store references in app state
    app.state.mcp_manager = mcp_manager
    app.state.container_manager = container_manager
    app.state.get_async_session = get_async_session
    app.state.transport_mode = transport_mode

    if oauth_provider:
        app.state.oauth_provider = oauth_provider

    logger.info(f"Application initialized in {transport_mode} mode")

    return app
