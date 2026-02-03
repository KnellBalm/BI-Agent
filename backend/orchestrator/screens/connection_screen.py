import json
import logging
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, OptionList, Button, Checkbox
from textual.widgets.option_list import Option
from textual.screen import ModalScreen

logger = logging.getLogger("tui")

class ConnectionScreen(ModalScreen):
    """
    데이터 소스 연결 설정 화면 (Step 3)
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
        height: 55;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 1 2;
    }
    #conn-title {
        text-align: center;
        color: #f8fafc;
        text-style: bold;
        margin-bottom: 1;
    }
    #conn-layout {
        layout: horizontal;
        height: 1fr;
    }
    #left-panel {
        width: 40;
        border-right: solid #2d2f34;
        padding-right: 1;
    }
    #right-panel {
        width: 1fr;
        padding-left: 1;
    }
    #existing-conn-list {
        height: 1fr;
        background: #111214;
        border: solid #2d2f34;
        margin-bottom: 1;
    }
    #conn-type-list {
        height: 5;
        margin-bottom: 1;
        background: #111214;
        border: solid #2d2f34;
    }
    .field-row {
        layout: horizontal;
        height: 3;
        margin-bottom: 0;
    }
    .field-label {
        width: 15;
        color: #94a3b8;
        content-align: left middle;
    }
    .conn-input {
        width: 1fr;
        background: #111214;
        border: solid #2d2f34;
        color: #f8fafc;
        height: 3;
    }
    .conn-input:focus {
        border: solid #7c3aed;
    }
    #connect-btn {
        width: 100%;
        background: #7c3aed;
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
    #error-feedback {
        background: #2d0a0a;
        color: #f87171;
        padding: 0 1;
        margin-top: 1;
        border: solid #991b1b;
        display: none;
        height: 4;
    }
    .ssh-group {
        border: solid #404040;
        padding: 0 1;
        margin-top: 1;
        background: #1a1b1e;
    }
    """
    
    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback
        self.selected_type = "sqlite"
        self.selected_conn_id = None  # Track selected connection for edit/delete
        self.use_ssh = False
        self.ssh_auth_type = "key"  # "key" or "password"
    
    def compose(self) -> ComposeResult:
        with Container(id="conn-modal"):
            yield Label("Data Source Manager", id="conn-title")
            
            with Container(id="conn-layout"):
                # Left Panel: Existing connections and type selection
                with Vertical(id="left-panel"):
                    yield Label("[bold]1. Select or Manage:[/bold]")
                    yield OptionList(id="existing-conn-list")
                    with Horizontal(id="action-bar"):
                        yield Button("Connect", id="active-btn", classes="action-btn-primary")
                        yield Button("Edit", id="edit-btn", classes="action-btn")
                        yield Button("Delete", id="delete-btn", classes="action-btn")
                    
                    yield Label("\n[bold]2. Create New Type:[/bold]")
                    yield OptionList(
                        Option("📂 Excel/CSV", id="excel"),
                        Option("🗄️ SQLite", id="sqlite"),
                        Option("🐘 PostgreSQL", id="postgres"),
                        Option("🐬 MySQL/Maria", id="mysql"),
                        id="conn-type-list"
                    )
                
                # Right Panel: Dynamic Form
                with VerticalScroll(id="right-panel"):
                    yield Label("[bold]3. Connection Details:[/bold]")
                    
                    with Horizontal(classes="field-row"):
                        yield Label("연결ID(Name):", classes="field-label")
                        yield Input(id="conn-id", placeholder="예: prod_db", classes="conn-input")
                    
                    with Horizontal(classes="field-row"):
                        yield Label("호스트(Host):", classes="field-label", id="path-label")
                        yield Input(id="conn-path", placeholder="IP 또는 파일경로", classes="conn-input")
                    
                    with Horizontal(classes="field-row", id="port-row"):
                        yield Label("포트(Port):", classes="field-label", id="port-label")
                        yield Input(id="conn-port", placeholder="5432", classes="conn-input")
                    
                    with Horizontal(classes="field-row", id="db-row"):
                        yield Label("DB명(Database):", classes="field-label", id="db-label")
                        yield Input(id="conn-db", placeholder="예: mydb", classes="conn-input")
                    
                    with Horizontal(classes="field-row", id="user-row"):
                        yield Label("사용자(User):", classes="field-label", id="user-label")
                        yield Input(id="conn-user", placeholder="DB 접속 계정", classes="conn-input")
                    
                    with Horizontal(classes="field-row", id="pass-row"):
                        yield Label("비밀번호(PW):", classes="field-label", id="pass-label")
                        yield Input(id="conn-pass", placeholder="DB 비밀번호", classes="conn-input", password=True)
                    
                    yield Label("\n🔐 [bold]SSH 터널링(Tunneling)[/bold]")
                    yield Checkbox("SSH 터널 사용", id="ssh-checkbox", value=False)
                    
                    with Vertical(id="ssh-group", classes="ssh-group"):
                        with Horizontal(classes="field-row"):
                            yield Label("SSH 호스트:", classes="field-label")
                            yield Input(id="ssh-host", placeholder="SSH 서버 IP", classes="conn-input")
                        with Horizontal(classes="field-row"):
                            yield Label("SSH 포트:", classes="field-label")
                            yield Input(id="ssh-port", value="22", classes="conn-input")
                        with Horizontal(classes="field-row"):
                            yield Label("SSH 계정:", classes="field-label")
                            yield Input(id="ssh-username", placeholder="SSH 사용자명", classes="conn-input")
                        
                        yield OptionList(
                            Option("🔑 키 파일(Key)", id="key"),
                            Option("🔒 비밀번호(PW)", id="password"),
                            id="ssh-auth-type"
                        )
                        
                        with Horizontal(classes="field-row", id="ssh-key-row"):
                            yield Label("키 경로:", classes="field-label")
                            yield Input(id="ssh-key-path", placeholder="~/.ssh/id_rsa", classes="conn-input")
                        
                        with Horizontal(classes="field-row", id="ssh-pass-row"):
                            yield Label("SSH 비번:", classes="field-label")
                            yield Input(id="ssh-password", password=True, placeholder="SSH 비밀번호", classes="conn-input")
                    
                    yield Button("저장 및 연결 (Save & Connect)", id="connect-btn", variant="primary")
                    yield Label("", id="error-feedback")
            
            yield Label("[dim]Esc:Close | Tab:Next | C:Connect | E:Edit | D:Delete[/dim]", classes="guide-text")
    
    def on_mount(self) -> None:
        self.query_one("#conn-type-list").focus()
        self._update_form("sqlite")
        self._load_existing_connections()
        self._hide_ssh_fields()  # SSH 필드 초기에는 숨김
        self._update_ssh_auth_fields()  # SSH 인증 타입 기본 설정
    
    def _load_existing_connections(self):
        try:
            with open(self.app.conn_mgr.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            list_view = self.query_one("#existing-conn-list", OptionList)
            list_view.clear_options()
            
            if not registry:
                list_view.add_option(Option("[dim]No connections registered yet[/dim]", id="none"))
            else:
                for conn_id, info in registry.items():
                    list_view.add_option(Option(f"{info['type'].upper()}: {conn_id} ({info.get('name', '')})", id=conn_id))
        except Exception as e:
            logger.error(f"Failed to load existing connections: {e}")
    
    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "existing-conn-list":
            if event.option.id == "none":
                return
            # Store selection and fill form for edit/delete, but don't dismiss
            conn_id = str(event.option.id)
            self.selected_conn_id = conn_id
            self._fill_form(conn_id)
        elif event.option_list.id == "conn-type-list":
            self.selected_type = str(event.option.id)
            self._update_form(self.selected_type)
        elif event.option_list.id == "ssh-auth-type":
            self.ssh_auth_type = str(event.option.id)
            self._update_ssh_auth_fields()
    
    def _fill_form(self, conn_id: str):
        """Populates the form with existing connection details for editing."""
        try:
            with open(self.app.conn_mgr.registry_path, 'r', encoding='utf-8') as f:
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
            
            # SSH handling
            ssh_info = info.get('ssh')
            checkbox = self.query_one("#ssh-checkbox", Checkbox)
            if ssh_info:
                checkbox.value = True
                self.use_ssh = True
                self._show_ssh_fields()
                self.query_one("#ssh-host", Input).value = ssh_info.get('host', '')
                self.query_one("#ssh-port", Input).value = str(ssh_info.get('port', '22'))
                self.query_one("#ssh-username", Input).value = ssh_info.get('username', '')
                
                if 'key_path' in ssh_info:
                    self.ssh_auth_type = "key"
                    self.query_one("#ssh-key-path", Input).value = ssh_info['key_path']
                else:
                    self.ssh_auth_type = "password"
                    self.query_one("#ssh-password", Input).value = ssh_info.get('password', '')
                
                self.query_one("#ssh-auth-type", OptionList).highlighted = 0 if self.ssh_auth_type == "key" else 1
                self._update_ssh_auth_fields()
            else:
                checkbox.value = False
                self.use_ssh = False
                self._hide_ssh_fields()
        
        except Exception as e:
            logger.error(f"Failed to fill form for {conn_id}: {e}")
    
    def _update_form(self, conn_type: str):
        path_label = self.query_one("#path-label", Label)
        path_input = self.query_one("#conn-path", Input)
        port_row = self.query_one("#port-row")
        db_row = self.query_one("#db-row")
        user_row = self.query_one("#user-row")
        pass_row = self.query_one("#pass-row")
        
        if conn_type in ["sqlite", "excel"]:
            path_label.update("File Path:")
            path_input.placeholder = "/path/to/file"
            port_row.display = False
            db_row.display = False
            user_row.display = False
            pass_row.display = False
        else:
            path_label.update("Host / Server:")
            path_input.placeholder = "localhost or IP"
            port_row.display = True
            db_row.display = True
            user_row.display = True
            pass_row.display = True
            
            port_input = self.query_one("#conn-port", Input)
            if not port_input.value:
                port_input.value = "5432" if conn_type == "postgres" else "3306"
    
    def _hide_ssh_fields(self):
        """SSH 관련 모든 필드 숨김"""
        self.query_one("#ssh-group").display = False
    
    def _show_ssh_fields(self):
        """SSH 관련 모든 필드 표시"""
        self.query_one("#ssh-group").display = True
        self._update_ssh_auth_fields()
    
    def _update_ssh_auth_fields(self):
        """SSH 인증 타입에 따라 Key Path / Password 필드 표시/숨김"""
        if not self.use_ssh:
            return
        
        key_row = self.query_one("#ssh-key-row")
        pass_row = self.query_one("#ssh-pass-row")
        
        if self.ssh_auth_type == "key":
            key_row.display = True
            pass_row.display = False
        else:  # password
            key_row.display = False
            pass_row.display = True
    
    def on_checkbox_changed(self, event) -> None:
        """SSH Tunnel 체크박스 상태 변경 핸들러"""
        if event.checkbox.id == "ssh-checkbox":
            self.use_ssh = event.value
            if self.use_ssh:
                self._show_ssh_fields()
                # SSH Host를 DB Host와 동일하게 자동 채우기
                db_host = self.query_one("#conn-path", Input).value.strip()
                ssh_host_input = self.query_one("#ssh-host", Input)
                if db_host and not ssh_host_input.value:
                    ssh_host_input.value = db_host
            else:
                self._hide_ssh_fields()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["active-btn", "edit-btn", "delete-btn"]:
            ol = self.query_one("#existing-conn-list", OptionList)
            if ol.highlighted is None:
                self.notify("Please select a connection first.", severity="warning")
                return
            
            conn_id = ol.get_option_at_index(ol.highlighted).id
            if conn_id == "none": return
            
            if event.button.id == "active-btn":
                # Immediately activate/notify orchestrator
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
                    "dbname": self.query_one("#conn-db", Input).value.strip(),
                    "user": self.query_one("#conn-user", Input).value.strip(),
                    "password": self.query_one("#conn-pass", Input).value
                }
                
                if self.use_ssh:
                    ssh_host = self.query_one("#ssh-host", Input).value.strip()
                    ssh_port = self.query_one("#ssh-port", Input).value.strip()
                    ssh_username = self.query_one("#ssh-username", Input).value.strip()
                    ssh_password = self.query_one("#ssh-password", Input).value.strip()
                    ssh_key_path = self.query_one("#ssh-key-path", Input).value.strip()
                    
                    if not all([ssh_host, ssh_port, ssh_username]):
                        self.notify("⚠️ SSH Host, Port, and Username are required.", severity="warning")
                        return
                    
                    ssh_config = {
                        "host": ssh_host,
                        "port": int(ssh_port),
                        "username": ssh_username,
                        "remote_host": "127.0.0.1", # Default for local db access over tunnel
                        "remote_port": int(config.get('port', 0))
                    }
                    
                    if self.ssh_auth_type == "key":
                        if not ssh_key_path:
                            self.notify("⚠️ SSH Key Path is required.", severity="warning")
                            return
                        ssh_config["key_path"] = ssh_key_path
                    else:
                        if not ssh_password:
                            self.notify("⚠️ SSH Password is required.", severity="warning")
                            return
                        ssh_config["password"] = ssh_password
                    
                    config["ssh"] = ssh_config
            
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
    
    def action_activate_connect(self) -> None:
        """Keyboard shortcut C to connect."""
        ol = self.query_one("#existing-conn-list", OptionList)
        if ol.highlighted is None:
            self.notify("먼저 연결을 선택해 주세요.", severity="warning")
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
            self.notify("먼저 연결을 선택해 주세요.", severity="warning")
            return
        conn_id = ol.get_option_at_index(ol.highlighted).id
        if conn_id == "none": return
        self._fill_form(str(conn_id))
        self.notify(f"Editing {conn_id}...", severity="information")
    
    def action_activate_delete(self) -> None:
        """Keyboard shortcut D to delete."""
        ol = self.query_one("#existing-conn-list", OptionList)
        if ol.highlighted is None:
            self.notify("먼저 연결을 선택해 주세요.", severity="warning")
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
