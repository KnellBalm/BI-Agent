#!/usr/bin/env python3
"""
Connection Lifecycle Management for MCP Servers

Provides:
- Signal handlers for graceful shutdown (SIGTERM, SIGINT)
- Lazy connection pool initialization pattern
- Cleanup registry for multiple resources
"""
import asyncio
import signal
import sys
from typing import Callable, List, Awaitable

_cleanup_handlers: List[Callable[[], Awaitable[None]]] = []


def register_cleanup(handler: Callable[[], Awaitable[None]]) -> None:
    """Register a cleanup handler to be called on shutdown.

    Args:
        handler: Async function to call during cleanup
    """
    _cleanup_handlers.append(handler)


async def run_cleanup() -> None:
    """Execute all registered cleanup handlers.

    Runs all cleanup handlers in order, catching and logging any errors.
    """
    for handler in _cleanup_handlers:
        try:
            await handler()
        except Exception as e:
            print(f"Cleanup error: {e}", file=sys.stderr)
    print("All cleanup handlers executed", file=sys.stderr)


def setup_signal_handlers() -> None:
    """Setup SIGTERM/SIGINT handlers for graceful shutdown.

    Registers signal handlers to execute cleanup on process termination.
    Includes Windows fallback for platforms that don't support add_signal_handler.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    def handle_signal():
        asyncio.create_task(run_cleanup())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: asyncio.create_task(run_cleanup()))


def log_startup(server_name: str) -> None:
    """Log server startup to stderr (stdout reserved for MCP protocol).

    Args:
        server_name: Name of the MCP server
    """
    print(f"{server_name} running on stdio", file=sys.stderr)


def log_error(message: str) -> None:
    """Log error to stderr.

    Args:
        message: Error message to log
    """
    print(f"ERROR: {message}", file=sys.stderr)
