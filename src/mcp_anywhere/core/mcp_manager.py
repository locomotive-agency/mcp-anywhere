"""MCP Manager for handling dynamic server mounting and unmounting."""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from mcp_anywhere.config import Config
from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.database import MCPServer
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.security.file_manager import SecureFileManager

logger = get_logger(__name__)

# Per-server docker --memory limit, with OOM escalation. mcp-anywhere spawns each
# server container with a fixed 512m limit; heavy servers (e.g. the Python sandbox)
# get OOM-killed. The crash watchdog escalates a server from 512m to 1g the first
# time it is OOM-killed, and persists that override under DATA_DIR so it survives
# app restarts. create_mcp_config reads the effective limit on every (re)mount.
DEFAULT_MEMORY_LIMIT = "512m"
ESCALATED_MEMORY_LIMIT = "1g"


def _mem_overrides_path() -> Path:
    return Path(Config.DATA_DIR) / "mem-overrides.json"


def get_server_memory_limit(server_id: str) -> str:
    """Effective docker --memory limit for a server (default 512m, escalated to 1g)."""
    try:
        data = json.loads(_mem_overrides_path().read_text())
        limit = data.get(server_id)
        return limit if isinstance(limit, str) and limit else DEFAULT_MEMORY_LIMIT
    except (OSError, ValueError):
        return DEFAULT_MEMORY_LIMIT


def set_server_memory_limit(server_id: str, limit: str) -> None:
    """Persist a per-server memory override under DATA_DIR."""
    path = _mem_overrides_path()
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data[server_id] = limit
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError as e:
        logger.error(f"Failed to persist memory override for {server_id}: {e}")


def create_mcp_config(server: "MCPServer") -> dict[str, dict[str, Any]]:
    """Create MCP proxy configuration for both new and existing containers.

    Args:
        server: Single MCPServer instance from database

    Returns:
        Dict containing both 'new' and 'existing' configuration options
    """
    container_manager = ContainerManager()

    # Use container manager's parsing logic for commands
    run_command = container_manager._parse_start_command(server)

    if not run_command:
        logger.warning(f"No start command for server {server.name}")
        return {"new": {}, "existing": {}}

    # Configuration for existing container (docker exec)
    container_name = container_manager._get_container_name(server.id)
    existing_config = {
        "command": "docker",
        "args": [
            "exec",
            "-i",  # Interactive (for stdio)
            container_name,  # Connect to existing container
            *run_command,  # The actual MCP command
        ],
        "env": {},
        "transport": "stdio",
    }

    # Configuration for new container (docker run)
    image_tag = container_manager.get_image_tag(server)

    # Extract environment variables (both regular and secret file paths)
    env_vars = container_manager._get_env_vars(server)
    env_args = []
    for key, value in env_vars.items():
        env_args.extend(["-e", f"{key}={value}"])

    # Prepare secret file volume mounts
    volume_args = []
    secret_files = getattr(server, "secret_files", [])

    if len(secret_files) > 0:
        file_manager = SecureFileManager()
        container_files = file_manager.prepare_container_files(server.id, secret_files)

        for source_path, container_path in container_files.items():
            # If we're a sibling container talking to the host docker daemon,
            # the daemon resolves bind sources against the host's filesystem,
            # not ours — translate before passing to docker run.
            host_source = container_manager.translate_to_host_path(source_path)
            volume_args.extend(["-v", f"{host_source}:{container_path}:ro"])

    # Persistent, writable per-server data directory.
    # mcp-anywhere spawns each server as a fresh sibling container, so anything
    # written inside the container's own filesystem is lost when the container
    # is rebuilt or recreated (on restart, or with CLEANUP_CONTAINERS_ON_SHUTDOWN).
    # Bind-mount a per-server directory that lives under DATA_DIR (the app's
    # persistent volume) at /data (read-write), so servers can keep state across
    # rebuilds — for example OAuth/MSAL token caches. translate_to_host_path maps
    # the source to the host path when running as a sibling container.
    persist_dir = Path(Config.DATA_DIR) / "server-data" / server.id
    persist_dir.mkdir(parents=True, exist_ok=True)
    host_persist_dir = container_manager.translate_to_host_path(str(persist_dir))
    volume_args.extend(["-v", f"{host_persist_dir}:/data:rw"])

    # Effective memory limit (512m default; the crash watchdog escalates to 1g on OOM).
    mem_limit = get_server_memory_limit(server.id)

    new_config = {
        "command": "docker",
        "args": [
            "run",
            # "--rm",  # Do not remove container immediately on exit
            "-i",  # Interactive (for stdio)
            "--name",
            container_name,  # Container name
            "--memory",
            mem_limit,  # Memory limit (512m default, 1g after an OOM kill)
            "--cpus",
            "0.5",  # CPU limit
            *env_args,  # Environment variables
            *volume_args,  # Secret file volume mounts
            image_tag,  # Our pre-built image
            *run_command,  # The actual MCP command
        ],
        "env": {},  # Already passed via docker -e
        "transport": "stdio",
        "init_timeout": 15,  # Add a 15-second initialization timeout
    }

    logger.debug(
        "docker run args for server %s: %s", server.name, new_config["args"]
    )

    return {"new": new_config, "existing": existing_config}


class MCPManager:
    """Manages the MCP Anywhere router and handles runtime server mounting/unmounting.

    This class encapsulates the FastMCP router and provides methods to dynamically
    add and remove MCP servers at runtime using FastMCP's mount() capability.
    """

    def __init__(self, router: FastMCP) -> None:
        """Initialize the MCP manager with a router."""
        self.router = router
        self.mounted_servers: dict[str, FastMCP] = {}
        logger.info("Initialized MCPManager")

    async def add_server(self, server_config: "MCPServer") -> list[dict[str, Any]]:
        """Add a new MCP server dynamically using FastMCP's mount capability.

        Args:
            server_config: The MCPServer database model

        Returns:
            List of discovered tools from the server
        """
        # Get both configuration options
        config_options = create_mcp_config(server_config)

        if not config_options["new"] and not config_options["existing"]:
            raise RuntimeError(
                f"Failed to create proxy config for {server_config.name}"
            )

        # Check container health and select appropriate config
        container_manager = ContainerManager()
        if container_manager._is_container_healthy(server_config):
            server_config_dict = config_options["existing"]
            logger.debug(f"Using existing container for {server_config.name}")
        else:
            server_config_dict = config_options["new"]
            logger.debug(f"Using new container for {server_config.name}")

        # Create proxy configuration in expected format
        proxy_config = {"mcpServers": {server_config.name: server_config_dict}}

        # Create FastMCP proxy for the server
        proxy = FastMCP.as_proxy(proxy_config)

        # Mount with 8-character prefix
        prefix = server_config.id
        self.router.mount(proxy, prefix=prefix)

        # Track the mounted server
        self.mounted_servers[server_config.id] = proxy

        logger.info(
            f"Successfully mounted server '{server_config.name}' with prefix '{prefix}'"
        )

        # Discover and return tools for existing containers
        return await self._discover_server_tools(server_config.id)

    def remove_server(self, server_id: str) -> None:
        """Remove an MCP server dynamically by unmounting it from all managers."""
        if server_id not in self.mounted_servers:
            logger.warning(f"Server '{server_id}' not found in mounted servers")
            return

        try:
            # Get the mounted server proxy
            mounted_server = self.mounted_servers[server_id]

            # Remove from all FastMCP internal managers
            # Based on FastMCP developer's example in issue #934
            for manager in [
                self.router._tool_manager,
                self.router._resource_manager,
                self.router._prompt_manager,
            ]:
                # Find and remove the mount for this server
                mounts_to_remove = [
                    m for m in manager._mounted_servers if m.server is mounted_server
                ]
                for mount in mounts_to_remove:
                    manager._mounted_servers.remove(mount)
                    logger.debug(f"Removed mount from {manager.__class__.__name__}")

            # FastMCP handles cache management internally

            # Remove from our tracking
            del self.mounted_servers[server_id]

            logger.info(
                f"Successfully unmounted server '{server_id}' from all managers"
            )

        except (RuntimeError, ValueError, KeyError) as e:
            logger.exception(f"Failed to remove server '{server_id}': {e}")
            raise

    async def _discover_server_tools(self, server_id: str) -> list[dict[str, Any]]:
        """Discover tools from a mounted server.

        Args:
            server_id: The ID of the server to discover tools from

        Returns:
            List of discovered tools with name and description
        """
        if server_id not in self.mounted_servers:
            return []

        try:
            tools = await self.mounted_servers[server_id]._tool_manager.get_tools()

            # Convert tools to the format expected by the database
            discovered_tools = []
            for key, tool in tools.items():
                discovered_tools.append(
                    {"name": key, "description": tool.description or ""}
                )

            logger.info(
                f"Discovered {len(discovered_tools)} tools for server '{server_id}'"
            )
            return discovered_tools

        except (RuntimeError, ValueError, ConnectionError, AttributeError) as e:
            logger.error(f"Failed to discover tools for server '{server_id}': {e}")

            # Check container logs for startup errors
            container_manager = ContainerManager()
            error_logs = container_manager.get_container_error_logs(server_id)

            if error_logs:
                # Try to extract a meaningful error message
                error_msg = container_manager._extract_error_from_logs(error_logs)
                if error_msg:
                    logger.error(
                        f"Container startup error for server '{server_id}': {error_msg}"
                    )
                    # Re-raise with the more meaningful error message
                    raise RuntimeError(f"Server startup failed: {error_msg}")

            # Re-raise the original error if no better error found
            raise


async def watchdog_loop(
    mcp_manager: "MCPManager",
    container_manager: ContainerManager,
    interval: int = 45,
) -> None:
    """Detect crashed server containers and re-mount just those, in place.

    mcp-anywhere proxies each server via a persistent ``docker run -i`` process that
    dies when the container crashes and is NOT auto-reconnected — leaving the server
    "running" (if restarted at the container level) but detached from the gateway.
    This background loop restores only the crashed server(s) by unmounting the stale
    proxy and re-mounting via the app's own add_server logic, without restarting the
    whole app. On an OOM kill it first escalates the container's memory limit from
    512m to 1g (persisted), so the re-mounted container gets more headroom.
    """
    from mcp_anywhere.database import get_active_servers, get_async_session

    logger.info(f"[watchdog] server-recovery loop started (interval={interval}s)")
    while True:
        try:
            await asyncio.sleep(interval)
            async with get_async_session() as session:
                servers = await get_active_servers(session)

            for server in servers:
                try:
                    if getattr(server, "build_status", None) != "built":
                        continue
                    if container_manager._is_container_healthy(server):
                        continue

                    name = container_manager._get_container_name(server.id)

                    # OOM escalation: bump 512m -> 1g the first time (check BEFORE cleanup,
                    # while the exited container still exists to report OOMKilled).
                    if (
                        container_manager.is_oom_killed(server.id)
                        and get_server_memory_limit(server.id) == DEFAULT_MEMORY_LIMIT
                    ):
                        set_server_memory_limit(server.id, ESCALATED_MEMORY_LIMIT)
                        logger.warning(
                            f"[watchdog] '{server.name}' was OOM-killed at "
                            f"{DEFAULT_MEMORY_LIMIT} -> escalating memory to "
                            f"{ESCALATED_MEMORY_LIMIT}"
                        )

                    logger.warning(
                        f"[watchdog] server '{server.name}' container is down — recovering"
                    )
                    # Free the container name so a fresh `docker run` can bind it.
                    container_manager._cleanup_existing_container(name)
                    # Drop the stale proxy, then re-mount cleanly (fresh docker run + connect).
                    mcp_manager.remove_server(server.id)
                    await mcp_manager.add_server(server)
                    logger.info(
                        f"[watchdog] server '{server.name}' recovered "
                        f"(memory={get_server_memory_limit(server.id)})"
                    )
                except Exception as e:  # one bad server must not stop the others
                    logger.error(
                        f"[watchdog] recovery failed for "
                        f"'{getattr(server, 'name', '?')}': {e}"
                    )
        except asyncio.CancelledError:
            logger.info("[watchdog] loop cancelled")
            raise
        except Exception as e:  # never let the watchdog die on a transient error
            logger.error(f"[watchdog] loop iteration error: {e}")
