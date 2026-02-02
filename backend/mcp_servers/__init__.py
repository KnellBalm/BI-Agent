"""
MCP Servers Package - Python Implementation

Common utilities and base patterns for Python MCP servers.
"""

import json
import sys
from typing import Any, Dict, List, Union

__version__ = "1.0.0"


def success_response(data: Any) -> str:
    """Create a successful JSON response.

    Args:
        data: Data to serialize to JSON

    Returns:
        JSON string with proper formatting
    """
    return json.dumps(data, indent=2, default=str)


def error_response(message: str) -> str:
    """Create an error JSON response.

    NOTE: With FastMCP, you should raise exceptions instead of using this.
    FastMCP automatically converts exceptions to isError: true responses.

    Args:
        message: Error message

    Returns:
        JSON string with error structure
    """
    return json.dumps({"error": message, "isError": True}, indent=2)


def log_info(message: str) -> None:
    """Log informational message to stderr.

    stdout is reserved for MCP protocol, all logging must go to stderr.

    Args:
        message: Message to log
    """
    print(f"INFO: {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Log error message to stderr.

    stdout is reserved for MCP protocol, all logging must go to stderr.

    Args:
        message: Error message to log
    """
    print(f"ERROR: {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """Log warning message to stderr.

    stdout is reserved for MCP protocol, all logging must go to stderr.

    Args:
        message: Warning message to log
    """
    print(f"WARNING: {message}", file=sys.stderr)
