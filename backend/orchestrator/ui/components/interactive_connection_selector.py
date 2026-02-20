import asyncio
import logging
from typing import Optional, Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, OptionList, Button, Label, Input
from textual.widgets.option_list import Option

from backend.orchestrator.managers.connection_manager import ConnectionManager

logger = logging.getLogger("tui")


class InteractiveConnectionSelector(Static):
    """
    A CLI-friendly inline widget for selecting or creating database connections.
    Replaces the tedious multi-step QuestionFlow.
    """
    
    DEFAULT_CSS = """
    InteractiveConnectionSelector {
        width: 100%;
        height: auto;
        min-height: 12;
        padding: 1;
        margin: 1 0;
        border-left: thick $accent;
        background: $surface;
    }
    
    .selector-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    OptionList {
        height: auto;
        min-height: 3;
        max-height: 10;
        border: none;
        background: transparent;
    }

    #add-conn-form {
        display: none;
        height: auto;
        margin-top: 1;
        border-top: dashed $surface-lighten-3;
        padding-top: 1;
    }
    
    .input-row {
        layout: horizontal;
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }
    
    .input-label {
        width: 15;
        text-align: right;
        margin-right: 1;
        color: $text-muted;
    }
    
    Input {
        width: 1fr;
        height: 1;
        border: none;
        background: $surface;
    }
    
    #form-buttons {
        layout: horizontal;
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
        height: 1;
        min-width: 10;
        border: none;
    }

    #help-label {
        margin-top: 1;
        color: $text-muted;
        font-size: 80%;
        text-align: center;
        width: 100%;
    }
    """

    def __init__(self, conn_mgr: ConnectionManager, on_connect=None, **kwargs):
        super().__init__(**kwargs)
        self.conn_mgr = conn_mgr
        self.on_connect_callback = on_connect  # Callback when a connection is selected

    def compose(self) -> ComposeResult:
        yield Label("🔌 Select or Create a Connection", classes="selector-title")
        yield OptionList(id="conn-list")
        
        # Add connection form (hidden by default)
        with Vertical(id="add-conn-form"):
            yield Label("[b]New Connection[/b] (SQLite/CSV/Excel format defaults to Path)", id="add-conn-title")
            
            with Horizontal(classes="input-row"):
                yield Label("ID:", classes="input-label")
                yield Input(placeholder="e.g., prod_db", id="input-id")
                
            with Horizontal(classes="input-row"):
                yield Label("Type:", classes="input-label")
                yield Input(placeholder="sqlite / postgresql / mysql", id="input-type", value="sqlite")
                
            with Horizontal(classes="input-row"):
                yield Label("Path/Host:", classes="input-label")
                yield Input(placeholder="File path or DB host", id="input-path")
                
            with Horizontal(id="form-buttons"):
                yield Button("Save & Connect", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
        
        yield Label("Enter: Connect | E: Edit | Del: Delete", id="help-label")

    def on_mount(self) -> None:
        self._refresh_list()
        self.query_one("#conn-list", OptionList).focus()

    def _refresh_list(self) -> None:
        option_list = self.query_one("#conn-list", OptionList)
        option_list.clear_options()
        
        connections = self.conn_mgr.list_connections()
        
        if connections:
            for idx, conn in enumerate(connections):
                conn_id = conn.get("id", f"unknown_{idx}")
                conn_type = conn.get("type", "unknown").upper()
                config = conn.get("config", {})
                
                # Format identifier based on type
                if conn_type in ("SQLITE", "EXCEL", "CSV"):
                    desc = config.get("path", "N/A")
                else:
                    host = config.get("host", "localhost")
                    port = config.get("port", "")
                    desc = f"{host}:{port}" if port else host
                    
                display = f"[cyan]{conn_id}[/cyan] [dim]({conn_type}) - {desc}[/dim]"
                option_list.add_option(Option(display, id=f"conn_{conn_id}"))
                
        option_list.add_option(Option("✨ [b]Add New Connection...[/b]", id="add_new"))

    def on_key(self, event) -> None:
        """Handle hotkeys for edit and delete."""
        if self.query_one("#add-conn-form").display:
            return

        option_list = self.query_one("#conn-list", OptionList)
        if option_list.highlighted is None:
            return

        selected_option = option_list.get_option_at_index(option_list.highlighted)
        selected_id = str(selected_option.id)

        if selected_id == "add_new":
            return

        conn_id = selected_id[5:]  # Remove 'conn_' prefix

        if event.key == "e":
            self._edit_connection(conn_id)
        elif event.key == "delete":
            self._confirm_delete(conn_id)

    def _edit_connection(self, conn_id: str) -> None:
        """Populate form with existing connection for editing."""
        conn = self.conn_mgr.get_connection(conn_id)
        if not conn:
            return
            
        self.query_one("#add-conn-title", Label).update(f"[b]Edit Connection: {conn_id}[/b]")
        self.query_one("#input-id", Input).value = conn_id
        # ID input should be disabled or marked as read-only if we don't want to change the key
        self.query_one("#input-id", Input).disabled = True 
        
        self.query_one("#input-type", Input).value = conn.get("type", "sqlite")
        
        config = conn.get("config", {})
        if conn.get("type") in ("sqlite", "excel", "csv"):
            self.query_one("#input-path", Input).value = config.get("path", "")
        else:
            host = config.get("host", "localhost")
            self.query_one("#input-path", Input).value = host

        self.query_one("#add-conn-form").display = True
        self.query_one("#conn-list").display = False
        self.query_one("#input-type", Input).focus()

    def _confirm_delete(self, conn_id: str) -> None:
        """Delete connection after basic verification."""
        try:
            if self.conn_mgr.delete_connection(conn_id):
                self.app.notify(f"Connection '{conn_id}' deleted.", severity="information")
                self._refresh_list()
        except Exception as e:
            self.app.notify(f"Error deleting connection: {e}", severity="error")

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_id = str(event.option.id)
        
        if selected_id == "add_new":
            self.query_one("#add-conn-form").display = True
            self.query_one("#conn-list").display = False
            self.query_one("#input-id", Input).focus()
        elif selected_id.startswith("conn_"):
            actual_conn_id = selected_id[5:]  # Remove 'conn_' prefix
            await self._trigger_connect(actual_conn_id)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.query_one("#add-conn-form").display = False
            self.query_one("#conn-list").display = True
            # Reset form for next time
            self.query_one("#add-conn-title", Label).update("[b]New Connection[/b] (SQLite/CSV/Excel format defaults to Path)")
            self.query_one("#input-id", Input).disabled = False
            self.query_one("#conn-list", OptionList).focus()
            
        elif event.button.id == "btn-save":
            conn_id = self.query_one("#input-id", Input).value.strip()
            conn_type = self.query_one("#input-type", Input).value.strip().lower()
            path_host = self.query_one("#input-path", Input).value.strip()
            
            if not conn_id or not path_host:
                self.app.notify("ID and Path/Host are required", severity="error")
                return
                
            # Naive config setup based on type
            if conn_type in ("sqlite", "excel", "csv"):
                config = {"path": path_host}
            else:
                config = {"host": path_host, "port": 5432} # Simplified for UX
                
            try:
                self.conn_mgr.register_connection(conn_id, conn_type, config)
                self.app.notify(f"Connection '{conn_id}' created successfully.", severity="information")
                await self._trigger_connect(conn_id)
            except Exception as e:
                self.app.notify(f"Error creating connection: {e}", severity="error")

    async def _trigger_connect(self, conn_id: str) -> None:
        """Call the callback with the selected connection ID and remove self."""
        if self.on_connect_callback:
            if asyncio.iscoroutinefunction(self.on_connect_callback):
                await self.on_connect_callback(conn_id)
            else:
                self.on_connect_callback(conn_id)
        
        # After successful connection selection, remove the widget
        self.remove()
