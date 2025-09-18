"""Command-line interface for MCP Anywhere.

Provides the main entry point for running MCP Anywhere in various modes
including HTTP server, STDIO server, and client connection modes.
"""

import argparse
import asyncio
import shutil
import signal
import sys

from mcp_anywhere.config import Config
from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.database import close_db
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.transport.http_server import run_http_server
from mcp_anywhere.transport.stdio_gateway import run_connect_gateway
from mcp_anywhere.transport.stdio_server import run_stdio_server

logger = get_logger(__name__)

# Global variable to track shutdown
_shutdown_requested = False


def setup_signal_handlers(loop) -> None:
    """Setup signal handlers for graceful shutdown."""

    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(cleanup_and_exit(loop, s)))


async def cleanup_and_exit(loop, sig) -> None:
    """Perform cleanup tasks and exit gracefully."""
    try:
        # Clean up containers
        container_manager = ContainerManager()
        await container_manager.cleanup_all_containers()

        # Close database connections
        await close_db()
        logger.info("Database connections closed.")

        logger.info("Shutdown complete.")

    except asyncio.CancelledError:
        logger.error("Cleanup Task Cancelled.")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        loop.remove_signal_handler(sig)

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for MCP Anywhere CLI.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="MCP Anywhere - Unified gateway for Model Context Protocol servers",
        prog="mcp-anywhere",
    )

    # Add subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    # Serve command - starts management server with MCP transport options
    serve_parser = subparsers.add_parser(
        "serve", help="Start the MCP Anywhere server with specified transport mode"
    )

    serve_subparsers = serve_parser.add_subparsers(
        dest="transport",
        help="MCP transport mode for client connections",
        required=True,
    )

    # HTTP transport mode
    http_parser = serve_subparsers.add_parser(
        "http",
        help="HTTP transport mode with OAuth 2.0 authentication for production deployments",
    )
    http_parser.add_argument(
        "--host", type=str, default=Config.DEFAULT_HOST, help="Host address to bind"
    )
    http_parser.add_argument(
        "--port", type=int, default=Config.DEFAULT_PORT, help="Port number to bind"
    )

    # STDIO transport mode
    stdio_parser = serve_subparsers.add_parser(
        "stdio",
        help="STDIO transport mode for local Claude Desktop integration",
    )
    stdio_parser.add_argument(
        "--host", type=str, default=Config.DEFAULT_HOST, help="Web interface host"
    )
    stdio_parser.add_argument(
        "--port", type=int, default=Config.DEFAULT_PORT, help="Web interface port"
    )

    # Connect command for MCP clients
    subparsers.add_parser(
        "connect", help="Connect as an MCP client via STDIO for direct tool access"
    )

    # Reset command
    reset_parser = subparsers.add_parser(
        "reset", help="Reset application data including database and configuration"
    )
    reset_parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompt"
    )

    return parser


def reset_data(confirm: bool = False) -> None:
    """Reset MCP Anywhere data by clearing the data directory.

    Args:
        confirm: Skip confirmation prompt if True
    """
    data_dir = Config.DATA_DIR

    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist. Nothing to reset.")
        return

    if not confirm:
        print(f"This will permanently delete all MCP Anywhere data in: {data_dir}")
        print("This includes:")
        print("  - Database (all servers, users, OAuth configurations)")
        print("  - OAuth 2.0 keys and tokens")
        print("  - Container build cache and logs")
        print()

        response = (
            input("Are you sure you want to continue? (yes/no): ").strip().lower()
        )
        if response not in ("yes", "y"):
            print("Reset cancelled.")
            return

    try:
        # Remove the entire data directory
        if data_dir.exists():
            shutil.rmtree(data_dir)
            print(f"Data directory removed: {data_dir}")

        # Recreate empty data directory
        data_dir.mkdir(exist_ok=True)
        print(f"Data directory created: {data_dir}")

        print("\nData reset completed.")
        print("The application will initialize with a fresh database on next startup.")

    except (OSError, PermissionError, FileNotFoundError) as e:
        print(f"Error during reset: {e}")
        sys.exit(1)


async def main() -> None:
    """Main entry point for MCP Anywhere application.

    Parses command-line arguments and calls the appropriate transport server
    function based on the chosen sub-command.
    """
    try:
        # Parse command-line arguments
        parser = create_parser()
        args = parser.parse_args()

        setup_signal_handlers(asyncio.get_running_loop())

        # Handle reset command (synchronous)
        if args.command == "reset":
            reset_data(confirm=args.confirm)
            return

        # Handle serve command (asynchronous)
        if args.command == "serve":
            if args.transport == "http":
                await run_http_server(host=args.host, port=args.port)

            elif args.transport == "stdio":
                await run_stdio_server(host=args.host, port=args.port)

        elif args.command == "connect":
            await run_connect_gateway()

        else:
            # This should not be reachable due to argparse configuration
            raise ValueError(f"Invalid command: {args.command}")

    except (ValueError, RuntimeError, ConnectionError) as e:
        # Only show errors for non-connect modes
        if args.command != "connect":
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def run_cli() -> None:
    """Synchronous entry point for CLI that properly handles async main."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
