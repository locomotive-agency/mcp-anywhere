"""MCP Manager for handling dynamic server mounting and unmounting."""

import asyncio
import json
import random
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from mcp_anywhere.config import Config
from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.core.instructions import schedule_instructions_refresh
from mcp_anywhere.core.tool_cache import tool_list_cache
from mcp_anywhere.database import MCPServer
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.security.file_manager import SecureFileManager

logger = get_logger(__name__)

# Per-server docker --memory limit, adjusted in both directions. mcp-anywhere spawns
# each server container with a fixed 512m limit; heavy servers (e.g. the Python
# sandbox) get OOM-killed. The crash watchdog escalates such a server to 1g and
# persists the override under DATA_DIR so it survives app restarts;
# create_mcp_config reads the effective limit on every (re)mount.
#
# Escalation is driven by the container's own cgroup limit counter, not by Docker's
# State.OOMKilled -- that flag is also set when the *host* ran out of memory and the
# kernel picked this container as its victim, and answering a host-wide shortage by
# handing out more memory makes the next shortage worse. See review_server_memory.
DEFAULT_MEMORY_LIMIT = "512m"
ESCALATED_MEMORY_LIMIT = "1g"

# De-escalation. Without a way back, an override is a ratchet: one unusual request
# costs a server double the memory for the life of the deployment, and on a host
# where the limits already sum to more than RAM, stale overrides make a global OOM
# likelier rather than less likely. A server is handed back to DEFAULT_MEMORY_LIMIT
# once its high-water mark has stayed well inside that limit for a long, quiet run.
# The measure is cgroup memory.peak, which resets when the container restarts, so a
# reading is always "peak during this run" and the uptime floor gives it weight.
DEESCALATE_PEAK_RATIO = 0.6
DEESCALATE_MIN_UPTIME_SECONDS = 7 * 24 * 60 * 60

# Bounds for the crash watchdog's sweep interval, in seconds. The actual delay is
# drawn fresh from this range before each pass rather than being a fixed tick.
WATCHDOG_MIN_INTERVAL = 300
WATCHDOG_MAX_INTERVAL = 600


def _mem_overrides_path() -> Path:
    return Path(Config.DATA_DIR) / "mem-overrides.json"


def get_server_memory_limit(server_id: str) -> str:
    """Effective docker --memory limit for a server (default 512m, escalated to 1g).

    A damaged overrides file must never be worse than a missing one: valid JSON that
    is not an object (``[]``, a bare string) would otherwise raise AttributeError out
    of this getter and fail every memory review, so the shape is checked rather than
    assumed -- matching the guard set_server_memory_limit already applies on write.
    """
    try:
        data = json.loads(_mem_overrides_path().read_text())
    except (OSError, ValueError):
        return DEFAULT_MEMORY_LIMIT
    if not isinstance(data, dict):
        return DEFAULT_MEMORY_LIMIT
    limit = data.get(server_id)
    return limit if isinstance(limit, str) and limit else DEFAULT_MEMORY_LIMIT


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


def clear_server_memory_limit(server_id: str) -> None:
    """Drop a server's memory override, returning it to DEFAULT_MEMORY_LIMIT.

    Takes effect at that server's next (re)mount, when create_mcp_config reads the
    effective limit again. Nothing is remounted here deliberately: a healthy server
    is not worth interrupting in order to give it *less* memory.
    """
    path = _mem_overrides_path()
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return
    if not isinstance(data, dict) or server_id not in data:
        return
    del data[server_id]
    try:
        path.write_text(json.dumps(data, indent=2))
    except OSError as e:
        logger.error(f"Failed to clear memory override for {server_id}: {e}")


_LIMIT_UNITS = {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}


def _limit_to_bytes(limit: str) -> int | None:
    """A docker memory string ("512m", "1g") in bytes, or None if unparseable."""
    text = limit.strip().lower()
    if not text:
        return None
    unit = _LIMIT_UNITS.get(text[-1])
    if unit is None:
        return int(text) if text.isdigit() else None
    digits = text[:-1]
    return int(digits) * unit if digits.isdigit() else None


def review_server_memory(
    server: "MCPServer", container_manager: ContainerManager
) -> None:
    """Move a running server's memory limit up or down on cgroup evidence.

    Up when the container has hit *its own* limit -- memory.events ``oom``, which the
    global OOM killer cannot increment. Down when it has demonstrably not needed the
    extra headroom for a long, quiet run.

    A container killed by a host-wide OOM lands here with kills but no limit event,
    and is deliberately left alone: it was not short of memory, the machine was.
    """
    stats = container_manager.read_cgroup_memory(server.id)
    if stats is None:
        return  # no evidence, which is not the same as no OOM

    current = get_server_memory_limit(server.id)

    if stats["limit_ooms"] > 0:
        if current == DEFAULT_MEMORY_LIMIT:
            set_server_memory_limit(server.id, ESCALATED_MEMORY_LIMIT)
            logger.warning(
                f"[watchdog] '{server.name}' reached its own {DEFAULT_MEMORY_LIMIT} "
                f"limit {stats['limit_ooms']}x (cgroup memory.events oom) -> "
                f"escalating to {ESCALATED_MEMORY_LIMIT}"
            )
        return

    if stats["kills"] > 0:
        logger.warning(
            f"[watchdog] '{server.name}' had {stats['kills']} OOM kill(s) without ever "
            f"reaching its own {current} limit -- host-level OOM, not escalating"
        )
        return

    if current == DEFAULT_MEMORY_LIMIT:
        return

    peak = stats["peak_bytes"]
    uptime = container_manager.container_uptime_seconds(server.id)
    default_bytes = _limit_to_bytes(DEFAULT_MEMORY_LIMIT)
    if peak is None or uptime is None or default_bytes is None:
        return
    if uptime < DEESCALATE_MIN_UPTIME_SECONDS:
        return
    if peak >= default_bytes * DEESCALATE_PEAK_RATIO:
        return

    clear_server_memory_limit(server.id)
    logger.info(
        f"[watchdog] '{server.name}' peaked at {peak // 1024 // 1024}MiB over "
        f"{uptime / 86400:.1f}d at {current} -> de-escalating to "
        f"{DEFAULT_MEMORY_LIMIT} (applies at its next remount)"
    )


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

        # The catalogue just changed; a cached listing would hide this server.
        tool_list_cache.invalidate(f"mounted '{server_config.name}'")
        schedule_instructions_refresh(self.router)

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
            # Same in reverse: a cached listing would keep advertising it.
            tool_list_cache.invalidate(f"unmounted '{server_id}'")
            schedule_instructions_refresh(self.router)

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
                    {
                        "name": key,
                        "description": tool.description or "",
                        # The input schema is what a caller needs to build arguments.
                        # It used to be dropped here, which left tool_schema empty for
                        # every tool and made the stored catalogue unusable for anything
                        # beyond listing names.
                        "schema": getattr(tool, "parameters", None),
                    }
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
    min_interval: int = WATCHDOG_MIN_INTERVAL,
    max_interval: int = WATCHDOG_MAX_INTERVAL,
) -> None:
    """Detect crashed server containers and re-mount just those, in place.

    mcp-anywhere proxies each server via a persistent ``docker run -i`` process that
    dies when the container crashes and is NOT auto-reconnected — leaving the server
    "running" (if restarted at the container level) but detached from the gateway.
    This background loop restores only the crashed server(s) by unmounting the stale
    proxy and re-mounting via the app's own add_server logic, without restarting the
    whole app. It also reviews the memory limit of every *healthy* server on each
    pass, escalating one that has hit its own cgroup limit and giving the override
    back once a server has proven it does not need the headroom.

    The delay between sweeps is re-randomized in ``[min_interval, max_interval]``
    before every pass. A permanently broken server (one whose container exits as
    soon as it is started) can never be recovered, so a fixed short interval turns
    into a tight retry loop against it; jittering a longer wait keeps that cheap and
    spreads the Docker API load instead of bunching it onto a fixed tick.
    """
    from mcp_anywhere.database import get_active_servers, get_async_session

    logger.info(
        f"[watchdog] server-recovery loop started "
        f"(interval={min_interval}-{max_interval}s, randomized per pass)"
    )
    while True:
        try:
            await asyncio.sleep(random.randint(min_interval, max_interval))
            async with get_async_session() as session:
                servers = await get_active_servers(session)

            for server in servers:
                try:
                    if getattr(server, "build_status", None) != "built":
                        continue
                    # Every Docker call below is blocking I/O on a client whose
                    # timeout is DOCKER_TIMEOUT (300s by default). This loop runs in
                    # the same event loop that serves HTTP, and the healthy path runs
                    # for every server on every sweep, so a stalled daemon would stall
                    # the gateway rather than just the watchdog. Hand them to threads.
                    if await asyncio.to_thread(
                        container_manager._is_container_healthy, server
                    ):
                        await asyncio.to_thread(
                            review_server_memory, server, container_manager
                        )
                        continue

                    name = container_manager._get_container_name(server.id)

                    # No escalation on this path. The only post-mortem signal Docker
                    # offers is State.OOMKilled, and it reads the same for a breach of
                    # the container's own limit as for a host-wide OOM that merely
                    # chose this container -- so acting on it would answer a shortage
                    # of host memory by promising out more of it. A server that really
                    # is short gets escalated by review_server_memory on a later
                    # sweep, from its own cgroup counter, once it is running again.
                    if await asyncio.to_thread(
                        container_manager.is_oom_killed, server.id
                    ):
                        logger.warning(
                            f"[watchdog] '{server.name}' exited OOM-killed; the cause "
                            f"(own limit vs host-wide) is not attributable after the "
                            f"fact -- recovering at "
                            f"{get_server_memory_limit(server.id)}"
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
