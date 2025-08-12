"""Custom MCP mount handler that properly manages FastMCP lifespan."""

import asyncio

from starlette.types import ASGIApp, Receive, Scope, Send

from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)


class FastMCPLifespanWrapper:
    """Wrapper that ensures FastMCP's lifespan is properly managed when mounted."""

    def __init__(self, fastmcp_app: ASGIApp) -> None:
        """Initialize with the FastMCP HTTP app."""
        self.fastmcp_app = fastmcp_app
        self.lifespan_task = None
        self.lifespan_started = False
        self.startup_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI handler that ensures lifespan is running before handling requests."""
        # Start lifespan if not already started
        if not self.lifespan_started:
            try:
                await self._ensure_lifespan_started()
            except Exception as e:
                logger.error(f"Failed to start FastMCP lifespan: {e}")
                # Send error response instead of crashing
                if scope["type"] == "http":
                    response = {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [[b"content-type", b"text/plain"]],
                    }
                    await send(response)
                    await send({
                        "type": "http.response.body",
                        "body": b"MCP server initialization failed",
                    })
                    return

        # Forward the request to the FastMCP app
        try:
            await self.fastmcp_app(scope, receive, send)
        except Exception as e:
            logger.error(f"Error in FastMCP app: {e}")
            # For HTTP requests, try to send error response
            if scope["type"] == "http":
                try:
                    response = {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [[b"content-type", b"text/plain"]],
                    }
                    await send(response)
                    await send({
                        "type": "http.response.body",
                        "body": f"MCP connection error: {e}".encode(),
                    })
                except Exception:
                    # If we can't send error response, just pass
                    pass

    async def _ensure_lifespan_started(self) -> None:
        """Ensure the FastMCP lifespan is started."""
        if self.lifespan_started:
            return

        self.lifespan_started = True
        logger.info("Starting FastMCP lifespan manager")

        # Create a mock ASGI lifespan scope
        lifespan_scope = {
            "type": "lifespan",
            "asgi": {"version": "3.0"},
            "state": {},
        }

        startup_completed = asyncio.Event()
        startup_error = None

        # Create receive/send for lifespan protocol
        async def lifespan_receive():
            # First call returns startup
            if not self.startup_event.is_set():
                self.startup_event.set()
                return {"type": "lifespan.startup"}
            # Wait for shutdown
            await self.shutdown_event.wait()
            return {"type": "lifespan.shutdown"}

        async def lifespan_send(message) -> None:
            nonlocal startup_error
            if message["type"] == "lifespan.startup.complete":
                logger.info("FastMCP lifespan startup complete")
                startup_completed.set()
            elif message["type"] == "lifespan.startup.failed":
                error_msg = message.get("message", "Unknown error")
                logger.error(f"FastMCP lifespan startup failed: {error_msg}")
                startup_error = RuntimeError(f"FastMCP lifespan startup failed: {error_msg}")
                startup_completed.set()
            elif message["type"] == "lifespan.shutdown.complete":
                logger.info("FastMCP lifespan shutdown complete")
            elif message["type"] == "lifespan.shutdown.failed":
                logger.error(
                    f"FastMCP lifespan shutdown failed: {message.get('message', 'Unknown error')}"
                )

        # Start the lifespan in a background task
        self.lifespan_task = asyncio.create_task(
            self.fastmcp_app(lifespan_scope, lifespan_receive, lifespan_send)
        )

        # Wait for startup to complete or fail (with timeout)
        try:
            await asyncio.wait_for(startup_completed.wait(), timeout=30.0)
            if startup_error:
                raise startup_error
        except asyncio.TimeoutError:
            logger.error("FastMCP lifespan startup timed out after 30 seconds")
            if self.lifespan_task and not self.lifespan_task.done():
                self.lifespan_task.cancel()
            raise RuntimeError("FastMCP lifespan startup timeout")
        except Exception as e:
            logger.error(f"Error during FastMCP lifespan startup: {e}")
            if self.lifespan_task and not self.lifespan_task.done():
                self.lifespan_task.cancel()
            raise

    async def shutdown(self) -> None:
        """Shutdown the FastMCP lifespan."""
        if self.lifespan_task and not self.lifespan_task.done():
            logger.info("Shutting down FastMCP lifespan")
            self.shutdown_event.set()
            try:
                # Give more time for graceful shutdown (increased from 5s to 10s)
                await asyncio.wait_for(self.lifespan_task, timeout=10.0)
            except TimeoutError:
                logger.warning("FastMCP lifespan shutdown timed out after 10 seconds")
                self.lifespan_task.cancel()
                try:
                    await self.lifespan_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error(f"Error during FastMCP lifespan shutdown: {e}")
                if not self.lifespan_task.done():
                    self.lifespan_task.cancel()
                    try:
                        await self.lifespan_task
                    except asyncio.CancelledError:
                        pass


async def create_mcp_mount_with_lifespan(mcp_manager):
    """Create a properly wrapped FastMCP HTTP app with lifespan management.

    Args:
        mcp_manager: The MCP manager containing the router

    Returns:
        FastMCPLifespanWrapper: Wrapped app that manages lifespan
    """
    # Create the FastMCP HTTP app
    mcp_http_app = mcp_manager.router.http_app(path="/", transport="http")

    # Wrap it with our lifespan manager
    wrapped_app = FastMCPLifespanWrapper(mcp_http_app)

    # Start the lifespan immediately
    await wrapped_app._ensure_lifespan_started()

    return wrapped_app
