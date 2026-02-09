import json
import logging
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, OptionList, Button
from textual.widgets.option_list import Option
from textual.screen import ModalScreen

logger = logging.getLogger("tui")

class ConnectionScreen(ModalScreen):
    """
    데이터 소스 연결 설정 화면 (Step 3) - Simplified
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("tab", "focus_next", "Next Field"),
        ("shift+tab", "focus_previous", "Prev Field"),
        ("c", "activate_connect", "Connect"),
        ("e", "activate_edit", "Edit"),
        ("d", "activate_delete", "Delete"),
    ]

    CSS = """
    ConnectionScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #conn-modal {
        width: 100;
        height: 40;
        background: $surface;
        border: solid $panel;
        padding: 1 2;
    }
    #conn-title {
        text-align: center;
        color: $text;
        text-style: bold;
        margin-bottom: 1;
    }
    #conn-layout {
        layout: horizontal;
        height: 1fr;
    }
    #left-panel {
        width: 40;
        border-right: solid $panel;
        padding-right: 1;
    }
    #right-panel {
        width: 1fr;
        padding-left: 1;
    }
    #existing-conn-list {
        height: 1fr;
        background: #111214;
        border: solid $panel;
        margin-bottom: 1;
    }
    #conn-type-list {
        height: 5;
        margin-bottom: 1;
        background: #111214;
        border: solid $panel;
    }
    .field-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }
    #connect-btn {
        width: 100%;
        background: $primary;
        color: white;
        margin-top: 1;
        text-style: bold;
    }
    #action-bar {
        layout: horizontal;
        height: 3;
        margin-top: 1;
    }
    .action-btn {
        width: 1fr;
        margin-right: 1;
    }
    .action-btn-primary {
        width: 1fr;
        margin-right: 1;
        background: #0ea5e9;
        color: white;
        text-style: bold;
    }
    #delete-btn {
        margin-right: 0;
        background: #991b1b;
        color: white;
    }
    #edit-btn {
        background: #1e40af;
        color: white;
    }
    #load-file-btn {
        width: 100%;
        margin-top: 1;
        background: #059669;
        color: white;
    }
    #env-hint {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    #error-feedback {
        background: #2d0a0a;
        color: #f87171;
        padding: 0 1;
        margin-top: 1;
        border: solid #991b1b;
        display: none;
        height: 4;
    }
    """

    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback
        self.selected_type = "sqlite"
        self.selected_conn_id = None

    def compose(self) -> ComposeResult:
        with Container(id="conn-modal"):
            yield Label("Data Source Manager", id="conn-title")

            with Container(id="conn-layout"):
                # Left Panel
                with Vertical(id="left-panel"):
                    yield Label("[bold]1. Select or Manage:[/bold]")
                    yield OptionList(id="existing-conn-list")
                    with Horizontal(id="action-bar"):
                        yield Button("Connect", id="active-btn", classes="action-btn-primary")
                        yield Button("Edit", id="edit-btn", classes="action-btn")
                        yield Button("Delete", id="delete-btn", classes="action-btn")

                    yield Button("Load from File...", id="load-file-btn")

                    yield Label("\n[bold]2. Create New Type:[/bold]")
                    yield OptionList(
                        Option("📂 Excel/CSV", id="excel"),
                        Option("🗄️ SQLite", id="sqlite"),
                        Option("🐘 PostgreSQL", id="postgres"),
                        Option("🐬 MySQL/Maria", id="mysql"),
                        id="conn-type-list"
                    )

                # Right Panel - Single Form
                with VerticalScroll(id="right-panel"):
                    yield Label("[bold]Connection Details[/bold]", classes="section-title")

                    with Container(classes="field-container", id="conn-id-container"):
                        yield Input(id="conn-id", placeholder="e.g., prod_db")

                    with Container(classes="field-container", id="path-container"):
                        yield Input(id="conn-path", placeholder="IP or File path")

                    with Horizontal(classes="field-row"):
                        with Container(classes="field-container", id="port-container"):
                            yield Input(id="conn-port", placeholder="5432")
                        with Container(classes="field-container", id="db-container"):
                            yield Input(id="conn-db", placeholder="database")

                    with Horizontal(classes="field-row"):
                        with Container(classes="field-container", id="user-container"):
                            yield Input(id="conn-user", placeholder="username")
                        with Container(classes="field-container", id="pass-container"):
                            yield Input(id="conn-pass", placeholder="password", password=True)

                    yield Label("[dim]Tip: Use ${VAR_NAME} for environment variables[/dim]", id="env-hint")

                    yield Button("Save & Connect", id="connect-btn", variant="primary")
                    yield Label("", id="error-feedback")

            yield Label("[dim]Esc:Close | Tab:Next | C:Connect | E:Edit | D:Delete[/dim]", classes="guide-text")

    def on_mount(self) -> None:
        self.query_one("#conn-type-list").focus()

        # Initialize Border Titles
        self.query_one("#conn-id-container").border_title = "Connection Name (ID)"
        self.query_one("#path-container").border_title = "Host / Path"
        self.query_one("#port-container").border_title = "Port"
        self.query_one("#db-container").border_title = "Database"
        self.query_one("#user-container").border_title = "Username"
        self.query_one("#pass-container").border_title = "Password"

        self._update_form("sqlite")
        self._load_existing_connections()

    def _load_existing_connections(self):
        try:
            storage_path = getattr(self.app.conn_mgr, 'storage_path', None) or getattr(self.app.conn_mgr, 'registry_path', None)
            if not storage_path:
                logger.warning("Could not determine connection storage path")
                return

            with open(storage_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            list_view = self.query_one("#existing-conn-list", OptionList)
            list_view.clear_options()

            if not registry:
                list_view.add_option(Option("[dim]No connections registered yet[/dim]", id="none"))
            else:
                for conn_id, info in registry.items():
                    list_view.add_option(Option(f"{info['type'].upper()}: {conn_id}", id=conn_id))
        except Exception as e:
            logger.error(f"Failed to load existing connections: {e}")

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "existing-conn-list":
            if event.option.id == "none":
                return
            conn_id = str(event.option.id)
            self.selected_conn_id = conn_id
            self._fill_form(conn_id)
        elif event.option_list.id == "conn-type-list":
            self.selected_type = str(event.option.id)
            self._update_form(self.selected_type)

    def _fill_form(self, conn_id: str):
        """Populates the form with existing connection details."""
        try:
            storage_path = getattr(self.app.conn_mgr, 'storage_path', None) or getattr(self.app.conn_mgr, 'registry_path', None)
            with open(storage_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            info = registry.get(conn_id)
            if not info: return

            self.selected_type = info['type']
            self._update_form(self.selected_type)

            self.query_one("#conn-id", Input).value = conn_id
            self.query_one("#conn-path", Input).value = info['config'].get('path', info['config'].get('host', ''))

            if self.selected_type in ["postgres", "mysql"]:
                self.query_one("#conn-port", Input).value = str(info['config'].get('port', ''))
                self.query_one("#conn-db", Input).value = info['config'].get('dbname', info['config'].get('database', ''))
                self.query_one("#conn-user", Input).value = info['config'].get('user', '')
                self.query_one("#conn-pass", Input).value = info['config'].get('password', '')
        except Exception as e:
            logger.error(f"Failed to fill form for {conn_id}: {e}")

    def _update_form(self, conn_type: str):
        path_container = self.query_one("#path-container")
        path_input = self.query_one("#conn-path", Input)
        port_container = self.query_one("#port-container")
        db_container = self.query_one("#db-container")
        user_container = self.query_one("#user-container")
        pass_container = self.query_one("#pass-container")

        if conn_type in ["sqlite", "excel"]:
            path_container.border_title = "File Path"
            path_input.placeholder = "/path/to/file.db"
            port_container.display = False
            db_container.display = False
            user_container.display = False
            pass_container.display = False
        else:
            path_container.border_title = "Host / Server"
            path_input.placeholder = "localhost or IP"
            port_container.display = True
            db_container.display = True
            user_container.display = True
            pass_container.display = True

            port_input = self.query_one("#conn-port", Input)
            if not port_input.value:
                port_input.value = "5432" if conn_type == "postgres" else "3306"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["active-btn", "edit-btn", "delete-btn"]:
            ol = self.query_one("#existing-conn-list", OptionList)
            if ol.highlighted is None:
                self.notify("Please select a connection first.", severity="warning")
                return

            conn_id = ol.get_option_at_index(ol.highlighted).id
            if conn_id == "none": return

            if event.button.id == "active-btn":
                self.dismiss(str(conn_id))
                if self.callback:
                    self.callback(str(conn_id))
            elif event.button.id == "edit-btn":
                self._fill_form(str(conn_id))
                self.notify(f"Editing {conn_id}...", severity="information")
            elif event.button.id == "delete-btn":
                try:
                    self.app.conn_mgr.delete_connection(str(conn_id))
                    self._load_existing_connections()
                    self.notify(f"🗑️ Deleted {conn_id}", severity="information")
                except Exception as e:
                    self.notify(f"Failed to delete: {e}", severity="error")

        elif event.button.id == "load-file-btn":
            await self._load_from_file()

        elif event.button.id == "connect-btn":
            conn_id = self.query_one("#conn-id", Input).value.strip()
            path = self.query_one("#conn-path", Input).value.strip()
            feedback = self.query_one("#error-feedback", Label)
            feedback.display = False

            if not conn_id or not path:
                self.notify("ID and Path are required!", severity="error")
                return

            config = {"path": path}
            if self.selected_type in ["postgres", "mysql"]:
                config = {
                    "host": path,
                    "port": int(self.query_one("#conn-port", Input).value.strip() or 0),
                    "database": self.query_one("#conn-db", Input).value.strip(),
                    "user": self.query_one("#conn-user", Input).value.strip(),
                    "password": self.query_one("#conn-pass", Input).value
                }

            try:
                self.app.conn_mgr.register_connection(conn_id, self.selected_type, config)
                self.dismiss(conn_id)
                if self.callback:
                    self.callback(conn_id)
            except Exception as e:
                logger.error(f"Connection registration failed: {e}")
                feedback.update(f"[bold red]Registration Failed:[/bold red]\n{str(e)[:200]}...")
                feedback.display = True
                self.notify(f"❌ Connection failed", severity="error")

    async def _load_from_file(self):
        """Load connections from YAML/JSON file."""
        try:
            from backend.agents.data_source.connection_file_loader import ConnectionFileLoader

            # Simple input prompt for file path
            from textual.widgets import Input as TextualInput
            from textual.screen import Screen

            # For now, use notify to ask for file path
            # TODO: Implement proper file picker dialog
            self.notify("Enter file path in terminal: /connect load <filepath>", severity="information")
        except Exception as e:
            logger.error(f"Failed to load from file: {e}")
            self.notify(f"Error: {e}", severity="error")

    def action_activate_connect(self) -> None:
        """Keyboard shortcut C to connect."""
        ol = self.query_one("#existing-conn-list", OptionList)
        if ol.highlighted is None:
            self.notify("Please select a connection first.", severity="warning")
            return
        conn_id = ol.get_option_at_index(ol.highlighted).id
        if conn_id == "none": return
        self.dismiss(str(conn_id))
        if self.callback:
            self.callback(str(conn_id))

    def action_activate_edit(self) -> None:
        """Keyboard shortcut E to edit."""
        ol = self.query_one("#existing-conn-list", OptionList)
        if ol.highlighted is None:
            self.notify("Please select a connection first.", severity="warning")
            return
        conn_id = ol.get_option_at_index(ol.highlighted).id
        if conn_id == "none": return
        self._fill_form(str(conn_id))
        self.notify(f"Editing {conn_id}...", severity="information")

    def action_activate_delete(self) -> None:
        """Keyboard shortcut D to delete."""
        ol = self.query_one("#existing-conn-list", OptionList)
        if ol.highlighted is None:
            self.notify("Please select a connection first.", severity="warning")
            return
        conn_id = ol.get_option_at_index(ol.highlighted).id
        if conn_id == "none": return
        try:
            self.app.conn_mgr.delete_connection(str(conn_id))
            self._load_existing_connections()
            self.notify(f"🗑️ Deleted {conn_id}", severity="information")
        except Exception as e:
            self.notify(f"Failed to delete: {e}", severity="error")

    def action_dismiss(self) -> None:
        self.dismiss(None)
