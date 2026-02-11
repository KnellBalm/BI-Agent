"""Connection flow for database connection management with full CRUD support."""

import logging
import os
import re
from typing import Any

from backend.orchestrator.services.question_flow import (
    FlowDefinition,
    FlowResult,
    Question,
)

logger = logging.getLogger(__name__)


def build_connection_flow(conn_mgr: Any, app: Any) -> FlowDefinition:
    """Build the connection flow with full CRUD support.

    Args:
        conn_mgr: ConnectionManager instance
        app: BiAgentConsole instance

    Returns:
        FlowDefinition: Complete connection flow with CRUD menu
    """

    # --- Shared state for dynamic defaults in edit mode ---
    answers: dict[str, Any] = {}
    selected_conn: dict[str, Any] | None = None

    # --- Validators ---

    def validate_conn_id(value: str) -> str | None:
        """Validate connection ID: alphanumeric + underscore only."""
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            return "Connection ID must contain only letters, numbers, and underscores."

        # Check for duplicates only in create mode
        existing_ids = [c["id"] for c in conn_mgr.list_connections()]
        if value in existing_ids and not answers.get("_edit_mode"):
            return f"Connection '{value}' already exists. Choose a different name."

        return None

    def validate_port(value: str) -> str | None:
        """Validate port number: numeric, 1-65535."""
        try:
            port = int(value)
            if not (1 <= port <= 65535):
                return "Port must be between 1 and 65535."
        except ValueError:
            return "Port must be a number."
        return None

    def validate_path(value: str) -> str | None:
        """Validate file path exists."""
        if not os.path.exists(value):
            return f"File not found: {value}"
        return None

    # --- Helper functions ---

    def format_connection_list() -> str:
        """Format existing connections as a numbered list."""
        connections = conn_mgr.list_connections()
        if not connections:
            return "[yellow]No connections found.[/yellow]"

        lines = ["[bold cyan]Existing Connections:[/bold cyan]\n"]
        for idx, conn in enumerate(connections, 1):
            conn_type = conn.get("type", "unknown").upper()
            conn_id = conn.get("id", "?")
            config = conn.get("config", {})

            # Format identifier based on type
            if conn_type in ("SQLITE", "EXCEL", "CSV"):
                identifier = config.get("path", "N/A")
            else:
                host = config.get("host", "localhost")
                port = config.get("port", "")
                identifier = f"{host}:{port}" if port else host

            lines.append(f"  [{idx}] {conn_type}: {conn_id} ({identifier})")

        return "\n".join(lines)

    def get_selected_connection() -> dict[str, Any] | None:
        """Retrieve the selected connection from answers."""
        nonlocal selected_conn
        if selected_conn is None:
            select_idx_str = answers.get("select_connection") or answers.get("select_connection_edit") or answers.get("select_connection_delete")
            if select_idx_str:
                try:
                    idx = int(select_idx_str) - 1
                    connections = conn_mgr.list_connections()
                    if 0 <= idx < len(connections):
                        selected_conn = connections[idx]
                except (ValueError, IndexError):
                    pass
        return selected_conn

    # --- Dynamic defaults for edit mode ---

    def default_conn_id(ans: dict) -> str:
        conn = get_selected_connection()
        return conn.get("id", "") if conn else ""

    def default_path_or_host(ans: dict) -> str:
        conn = get_selected_connection()
        if not conn:
            return ""
        config = conn.get("config", {})
        conn_type = ans.get("conn_type", "")
        if conn_type in ("sqlite", "excel", "csv"):
            return config.get("path", "")
        return config.get("host", "localhost")

    def default_port(ans: dict) -> str:
        conn = get_selected_connection()
        if not conn:
            return "5432"
        config = conn.get("config", {})
        return str(config.get("port", "5432"))

    def default_database(ans: dict) -> str:
        conn = get_selected_connection()
        if not conn:
            return ""
        config = conn.get("config", {})
        return config.get("database", config.get("dbname", ""))

    def default_user(ans: dict) -> str:
        conn = get_selected_connection()
        if not conn:
            return ""
        config = conn.get("config", {})
        return config.get("user", "")

    def default_password(ans: dict) -> str:
        conn = get_selected_connection()
        if not conn:
            return ""
        config = conn.get("config", {})
        return config.get("password", "")

    # --- Next question routing ---

    def next_after_action(ans: dict) -> str | None:
        """Route based on selected action."""
        nonlocal answers
        answers = ans
        action = ans.get("action")
        if action == "1":  # Connect to existing
            return "select_connection"
        elif action == "2":  # Create new
            ans["_edit_mode"] = False
            return "conn_type"
        elif action == "3":  # Edit existing
            ans["_edit_mode"] = True
            return "select_connection_edit"
        elif action == "4":  # Delete
            return "select_connection_delete"
        return None

    def next_after_select_connection(ans: dict) -> str | None:
        """After selecting connection to connect, complete flow."""
        nonlocal answers
        answers = ans
        return None

    def next_after_select_connection_edit(ans: dict) -> str | None:
        """After selecting connection to edit, go to conn_type."""
        nonlocal answers
        answers = ans
        # Preload selected connection's type
        conn = get_selected_connection()
        if conn:
            ans["conn_type"] = conn.get("type", "sqlite")
        return "conn_type"

    def next_after_select_connection_delete(ans: dict) -> str | None:
        """After selecting connection to delete, confirm."""
        nonlocal answers
        answers = ans
        return "confirm_delete"

    def next_after_conn_type(ans: dict) -> str | None:
        """Route based on connection type."""
        nonlocal answers
        answers = ans
        return "conn_id"

    def next_after_conn_id(ans: dict) -> str | None:
        """After conn_id, ask for path or host."""
        nonlocal answers
        answers = ans
        return "path_or_host"

    def next_after_path_or_host(ans: dict) -> str | None:
        """If file-based, complete. Otherwise ask for port."""
        nonlocal answers
        answers = ans
        conn_type = ans.get("conn_type", "")
        if conn_type in ("sqlite", "excel", "csv"):
            return None  # Complete
        return "port"

    def next_after_port(ans: dict) -> str | None:
        """After port, ask for database."""
        nonlocal answers
        answers = ans
        return "database"

    def next_after_database(ans: dict) -> str | None:
        """After database, ask for user."""
        nonlocal answers
        answers = ans
        return "user"

    def next_after_user(ans: dict) -> str | None:
        """After user, ask for password."""
        nonlocal answers
        answers = ans
        return "password"

    def next_after_password(ans: dict) -> str | None:
        """After password, complete flow."""
        nonlocal answers
        answers = ans
        return None

    def next_after_confirm_delete(ans: dict) -> str | None:
        """After delete confirmation, complete."""
        nonlocal answers
        answers = ans
        return None

    # --- Completion handlers ---

    async def on_complete(ans: dict) -> FlowResult:
        """Handle flow completion based on action."""
        nonlocal answers
        answers = ans
        action = ans.get("action")

        if action == "1":  # Connect to existing
            return await on_complete_connect(ans)
        elif action in ("2", "3"):  # Create or Edit
            return await on_complete_create_or_edit(ans)
        elif action == "4":  # Delete
            return await on_complete_delete(ans)

        # No action means direct create (no connections exist)
        if not action:
            return await on_complete_create_or_edit(ans)

        return FlowResult(success=False, message="Unknown action.")

    async def on_complete_connect(ans: dict) -> FlowResult:
        """Connect to an existing connection."""
        select_idx_str = ans.get("select_connection")
        try:
            idx = int(select_idx_str) - 1
            connections = conn_mgr.list_connections()
            if not (0 <= idx < len(connections)):
                return FlowResult(success=False, message="Invalid selection.")

            conn = connections[idx]
            conn_id = conn.get("id")

            # Trigger scan
            if hasattr(app, "_run_scan"):
                app.run_worker(app._run_scan(conn_id))

            return FlowResult(
                success=True,
                message=f"[green]✓[/green] Connected to '{conn_id}'."
            )
        except (ValueError, IndexError) as e:
            return FlowResult(success=False, message=f"Invalid selection: {e}")

    async def on_complete_create_or_edit(ans: dict) -> FlowResult:
        """Create or edit a connection."""
        conn_id = ans["conn_id"]
        conn_type = ans["conn_type"]
        edit_mode = ans.get("_edit_mode", False)

        # Build config based on connection type
        if conn_type in ("sqlite", "excel", "csv"):
            config = {"path": ans["path_or_host"]}
        else:
            config = {
                "host": ans["path_or_host"],
                "port": int(ans["port"]),
                "database": ans["database"],
                "user": ans["user"],
                "password": ans["password"],
            }

        try:
            # Register connection
            conn_mgr.register_connection(conn_id, conn_type, config)

            # Trigger scan
            if hasattr(app, "_run_scan"):
                app.run_worker(app._run_scan(conn_id))

            action_word = "updated" if edit_mode else "created"
            return FlowResult(
                success=True,
                message=f"[green]✓[/green] Connection '{conn_id}' {action_word} and connected!"
            )
        except Exception as e:
            logger.error(f"Failed to register connection: {e}")
            return FlowResult(
                success=False,
                message=f"[red]Failed to register connection: {e}[/red]"
            )

    async def on_complete_delete(ans: dict) -> FlowResult:
        """Delete a connection."""
        confirm = ans.get("confirm_delete", "").lower()
        if confirm not in ("y", "yes"):
            return FlowResult(success=False, message="Deletion cancelled.")

        conn = get_selected_connection()
        if not conn:
            return FlowResult(success=False, message="No connection selected.")

        conn_id = conn.get("id")

        try:
            conn_mgr.delete_connection(conn_id)
            return FlowResult(
                success=True,
                message=f"[yellow]Connection '{conn_id}' deleted.[/yellow]"
            )
        except Exception as e:
            logger.error(f"Failed to delete connection: {e}")
            return FlowResult(
                success=False,
                message=f"[red]Failed to delete connection: {e}[/red]"
            )

    # --- Question definitions ---

    # Check if connections exist
    has_connections = len(conn_mgr.list_connections()) > 0

    if has_connections:
        # Show CRUD menu
        q_action = Question(
            id="action",
            prompt=f"{format_connection_list()}\n\n[bold]What would you like to do?[/bold]",
            input_type="choice",
            choices=[
                ("1", "Connect to existing"),
                ("2", "Create new connection"),
                ("3", "Edit existing connection"),
                ("4", "Delete connection"),
            ],
            default="1",
            next_question=next_after_action,
        )
        first_question_id = "action"
    else:
        # Jump directly to create flow
        first_question_id = "conn_type"
        q_action = None  # Not used

    q_select_connection = Question(
        id="select_connection",
        prompt="Select a connection (enter number):",
        input_type="text",
        next_question=next_after_select_connection,
    )

    q_select_connection_edit = Question(
        id="select_connection_edit",
        prompt="Select a connection to edit (enter number):",
        input_type="text",
        next_question=next_after_select_connection_edit,
    )

    q_select_connection_delete = Question(
        id="select_connection_delete",
        prompt="Select a connection to delete (enter number):",
        input_type="text",
        next_question=next_after_select_connection_delete,
    )

    q_conn_type = Question(
        id="conn_type",
        prompt="Select connection type:",
        input_type="choice",
        choices=[
            ("sqlite", "SQLite"),
            ("postgresql", "PostgreSQL"),
            ("mysql", "MySQL"),
            ("excel", "Excel/CSV"),
        ],
        default="sqlite",
        next_question=next_after_conn_type,
    )

    q_conn_id = Question(
        id="conn_id",
        prompt="Connection name (alphanumeric + underscore):",
        input_type="text",
        default=default_conn_id,
        validator=validate_conn_id,
        next_question=next_after_conn_id,
    )

    q_path_or_host = Question(
        id="path_or_host",
        prompt=lambda ans: (
            "File path:" if ans.get("conn_type") in ("sqlite", "excel", "csv")
            else "Host address:"
        ),
        input_type="text",
        default=default_path_or_host,
        validator=lambda v: validate_path(v) if answers.get("conn_type") in ("sqlite", "excel", "csv") else None,
        next_question=next_after_path_or_host,
    )

    q_port = Question(
        id="port",
        prompt="Port number:",
        input_type="text",
        default=default_port,
        validator=validate_port,
        transform=int,
        next_question=next_after_port,
    )

    q_database = Question(
        id="database",
        prompt="Database name:",
        input_type="text",
        default=default_database,
        next_question=next_after_database,
    )

    q_user = Question(
        id="user",
        prompt="Username:",
        input_type="text",
        default=default_user,
        next_question=next_after_user,
    )

    q_password = Question(
        id="password",
        prompt="Password:",
        input_type="password",
        default=default_password,
        next_question=next_after_password,
    )

    q_confirm_delete = Question(
        id="confirm_delete",
        prompt=lambda ans: f"Delete connection '{get_selected_connection().get('id', '?') if get_selected_connection() else '?'}'? This cannot be undone. (y/n)",
        input_type="confirm",
        next_question=next_after_confirm_delete,
    )

    # Build question dictionary
    questions = {
        "conn_type": q_conn_type,
        "conn_id": q_conn_id,
        "path_or_host": q_path_or_host,
        "port": q_port,
        "database": q_database,
        "user": q_user,
        "password": q_password,
        "select_connection": q_select_connection,
        "select_connection_edit": q_select_connection_edit,
        "select_connection_delete": q_select_connection_delete,
        "confirm_delete": q_confirm_delete,
    }

    if q_action is not None:
        questions["action"] = q_action

    return FlowDefinition(
        flow_id="connection_setup",
        title="Connection Management",
        questions=questions,
        first_question=first_question_id,
        on_complete=on_complete,
    )
