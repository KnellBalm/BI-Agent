import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.widgets import Label, Input, ListView, ListItem, Static, Header, Footer, DataTable, RichLog, OptionList, Button, Checkbox
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.binding import Binding
from rich.markup import escape

from backend.orchestrator.auth_manager import auth_manager
from backend.orchestrator.quota_manager import quota_manager
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager
from backend.utils.diagnostic_logger import diagnostic_logger
from backend.orchestrator.error_viewer_screen import ErrorViewerScreen
import pandas as pd
from backend.orchestrator.hud_statusline import HUDStatusLine
from backend.orchestrator.message_components import (
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker
)
from backend.orchestrator.context_manager import context_manager
from backend.orchestrator.command_history import CommandHistory
from backend.orchestrator.screens.table_selection_screen import TableSelectionScreen
from backend.orchestrator.screens.visual_analysis_screen import VisualAnalysisScreen

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

class AuthScreen(ModalScreen):
    """
    LLM Provider 설정 안내 화면 (CLI-style)
    사용자에게 환경변수 또는 credentials.json 파일로 API 키를 설정하는 방법을 안내합니다.
    """
    
    CSS = """
    AuthScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #auth-modal {
        width: 70;
        height: auto;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 2 4;
    }
    #auth-title {
        text-align: center;
        color: #f8fafc;
        text-style: bold;
        margin-bottom: 1;
    }
    .guide-text {
        color: #94a3b8;
        margin: 1 0;
        text-align: center;
    }
    .credential-path {
        color: #7c3aed;
        text-style: bold italic;
        text-align: center;
    }
    #provider-list {
        height: 5;
        margin: 1 0;
        background: #111214;
        border: solid #2d2f34;
    }
    #detail-container {
        height: auto;
        margin: 1 0;
        padding: 1 2;
        background: #111214;
        border-left: tall #7c3aed;
    }
    #api-key-container {
        margin-top: 1;
        border: solid #2d2f34;
        background: #111214;
        padding: 1;
    }
    #api-key-input {
        background: #1a1b1e;
        border: solid #404040;
        margin-bottom: 1;
        color: #f8fafc;
        width: 100%;
    }
    #api-key-input:focus {
        border: solid #7c3aed;
    }
    #save-key-btn {
        width: 100%;
        background: #7c3aed;
        color: white;
        text-style: bold;
    }
    #save-key-btn:hover {
        background: #6d28d9;
    }
    """
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("1", "select_gemini", "Gemini"),
        ("2", "select_claude", "Claude"),
        ("3", "select_openai", "OpenAI"),
    ]
    
    def __init__(self):
        super().__init__()
        self.selected_provider = None
        logger.debug("AuthScreen initialized (CLI-style)")
    
    def compose(self) -> ComposeResult:
        with Container(id="auth-modal"):
            yield Label("LLM Provider Authentication", id="auth-title")
            
            yield Label("BI-Agent reads API keys automatically from your environment or config file.", classes="guide-text")
            yield Label(f"Config: ~/.bi-agent/credentials.json", classes="credential-path")
            
            yield OptionList(
                Option("🔑 Gemini (Google)", id="gemini"),
                Option("🤖 Claude (Anthropic)", id="claude"),
                Option("💡 ChatGPT (OpenAI)", id="openai"),
                id="provider-list"
            )
            
            yield Container(id="detail-container")
            
            with Vertical(id="api-key-container"):
                yield Label("[dim]Enter API Key manually:[/dim]")
                yield Input(id="api-key-input", placeholder="Paste your API key here...", password=True)
                yield Button("Save & Authenticate", id="save-key-btn")
            
            yield Label("\n[dim]Press ESC to skip if already configured.[/dim]", classes="guide-text")
    
    def on_mount(self) -> None:
        """화면 마운트 시 첫 번째 항목 선택"""
        logger.info("AuthScreen mounted - showing setup instructions")
        option_list = self.query_one("#provider-list", OptionList)
        option_list.focus()
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """사용자가 공급자를 선택했을 때 상세 안내 표시"""
        provider = event.option.id
        logger.info(f"User selected provider: {provider}")
        self.selected_provider = provider
        self._show_provider_details(provider)
    
    def _show_provider_details(self, provider: str) -> None:
        """선택한 공급자의 상세 설정 방법 표시"""
        try:
            detail_container = self.query_one("#detail-container", Container)
            detail_container.remove_children()
            
            details = {
                "gemini": {
                    "name": "Gemini (Google AI Studio)",
                    "env_var": "GEMINI_API_KEY",
                    "api_url": "https://aistudio.google.com/app/apikey",
                    "cred_key": "gemini"
                },
                "claude": {
                    "name": "Claude (Anthropic)",
                    "env_var": "ANTHROPIC_API_KEY",
                    "api_url": "https://console.anthropic.com/",
                    "cred_key": "claude"
                },
                "openai": {
                    "name": "ChatGPT (OpenAI)",
                    "env_var": "OPENAI_API_KEY",
                    "api_url": "https://platform.openai.com/api-keys",
                    "cred_key": "openai"
                }
            }
            
            info = details[provider]
            
            # compose() 외부에서는 with 구문 대신 직접 mount 호출
            detail_container.mount(Label(f"[bold cyan]{info['name']} 설정 방법[/bold cyan]"))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]방법 1: 환경변수 설정[/bold]"))
            detail_container.mount(Label(f"  export {info['env_var']}=\"your-api-key-here\""))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]방법 2: credentials.json 파일 편집[/bold]"))
            detail_container.mount(Label(f"  파일: ~/.bi-agent/credentials.json"))
            detail_container.mount(Label(f'  {{"providers": {{"{info["cred_key"]}": {{"key": "your-api-key-here"}}}}}}'))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]API 키 발급:[/bold] {info['api_url']}", classes="api-link"))
            
            logger.debug(f"Displayed setup details for {provider}")
        except Exception as e:
            logger.error(f"Error showing provider details: {e}", exc_info=True)
    
    def action_select_gemini(self) -> None:
        """숫자 키 1로 Gemini 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 0
        option_list.action_select()
    
    def action_select_claude(self) -> None:
        """숫자 키 2로 Claude 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 1
        option_list.action_select()
    
    def action_select_openai(self) -> None:
        """숫자 키 3로 OpenAI 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 2
        option_list.action_select()
    
    def action_dismiss(self) -> None:
        """ESC 키로 모달 닫기"""
        logger.info("AuthScreen dismissed by user")
        self.dismiss(False)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """API 키 저장 버튼 클릭"""
        if event.button.id == "save-key-btn":
            self._save_api_key()
    
    async def _save_api_key(self) -> None:
        """입력된 API 키를 검증 후 credentials.json에 저장"""
        if not self.selected_provider:
            self.notify("먼저 LLM 공급자를 선택해주세요!", severity="warning")
            return
        
        api_key_input = self.query_one("#api-key-input", Input)
        api_key = api_key_input.value.strip()
        
        if not api_key:
            self.notify("API 키를 입력해주세요!", severity="warning")
            return
        
        # 1. Ping Test 수행
        self.notify(f"🔍 {self.selected_provider.capitalize()} 키 유효성 검사 중...", severity="information")
        is_valid = await auth_manager.verify_key(self.selected_provider, api_key)
        
        if not is_valid:
            self.notify(f"❌ {self.selected_provider.capitalize()} API 키가 유효하지 않거나 연결에 실패했습니다.", severity="error")
            return

        try:
            # credentials.json 파일 경로
            creds_path = path_manager.home_dir / "credentials.json"
            
            # 기존 credentials 읽기 또는 새로 생성
            if creds_path.exists():
                with open(creds_path, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
            else:
                credentials = {"providers": {}}
            
            # API 키 저장
            if "providers" not in credentials:
                credentials["providers"] = {}
            
            credentials["providers"][self.selected_provider] = {"key": api_key}
            
            # 파일에 저장
            with open(creds_path, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)
            
            logger.info(f"API key verified and saved for {self.selected_provider}")
            self.notify(f"✅ {self.selected_provider.capitalize()} 인증에 성공했습니다!\n다음 단계: /connect 명령어로 데이터를 연결하세요.", severity="information")
            
            # 입력 필드 초기화
            api_key_input.value = ""
            
            # auth_manager에 즉시 반영
            auth_manager.load_credentials()
            
            # Journey Progress: Update to Auth step
            context_manager.update_journey_step(1)
            await self._update_sidebar()
            
            # 메인 앱의 상태 업데이트 트리거 (실제로 호출되진 않지만, notification으로 충분할 수 있음)
            # self.app.call_after_refresh(self.app._update_sidebar)
            
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            self.notify(f"❌ API 키 저장 실패: {e}", severity="error")

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

class ProjectScreen(ModalScreen):
    """
    Project selection and creation screen.
    """
    def __init__(self, current_project: str):
        super().__init__()
        self.current_project = current_project

    def compose(self) -> ComposeResult:
        with Vertical(id="project-modal"):
            yield Label("[bold white]Project Manager[/bold white]", id="project-title")
            yield Label(f"Current: [cyan]{self.current_project}[/cyan]\n")
            yield Label("Switch to or create a new project:")
            yield ListView(id="project-list")
            yield Input(id="new-project-input", placeholder="Enter new project name to create...")
            yield Label("\n[dim]Esc:Cancel  Enter:Select/Create[/dim]")

    CSS = """
    #project-modal {
        width: 50;
        height: 20;
        background: #1e293b;
        border: thick #10b981;
        padding: 2;
        align: center middle;
    }
    #project-title {
        text-align: center;
        margin-bottom: 1;
    }
    #project-list {
        height: 8;
        background: #0f172a;
        margin: 1 0;
    }
    """

    def on_mount(self) -> None:
        project_list = self.query_one("#project-list", ListView)
        project_list.clear()
        
        if not path_manager.projects_dir.exists():
            path_manager.projects_dir.mkdir(parents=True, exist_ok=True)
            
        projects = [d.name for d in path_manager.projects_dir.iterdir() if d.is_dir()]
        if not projects:
            projects = ["default"]
            
        self.proj_map = {}
        for idx, p in enumerate(projects):
            label = f"📁 {p}"
            if p == self.current_project:
                label += " [bold cyan](current)[/bold cyan]"
            project_list.append(ListItem(Label(label)))
            self.proj_map[idx] = p

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = self.query_one("#project-list", ListView).index
        if idx in self.proj_map:
            self.dismiss(self.proj_map[idx])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_name = event.value.strip()
        if new_name:
            self.dismiss(new_name)

class BI_AgentConsole(App):
    """
    분석가를 위한 지능형 관문 (Entrance Hall).
    대화형 인터페이스와 슬래시 명령어(/)를 통해 필요한 에이전트를 호출합니다.
    """
    CSS = """
    Screen {
        background: #0c0c0e;
    }
    #main-container {
        width: 100%;
        height: 100%;
    }
    #content-area {
        height: 1fr;
    }
    #chat-area {
        width: 1fr;
        height: 100%;
    }
    #chat-log {
        height: 1fr;
        border: none;
        background: #0c0c0e;
        padding: 1 2;
    }
    #input-bar {
        height: auto;
        margin: 0 1;
        background: #0c0c0e;
        border-top: solid #21262d;
        layout: vertical;
    }
    #command-menu {
        height: auto;
        max-height: 8;
        background: #161b22;
        border: solid #30363d;
        display: none;
        margin: 0 4;
        padding: 0 0;
    }
    #command-menu.visible {
        display: block;
    }
    #command-menu > .option-list--option {
        padding: 0 1;
    }
    #command-menu > .option-list--option-highlighted {
        background: #7c3aed;
        color: #f8fafc;
    }
    #input-container {
        height: 3;
        layout: horizontal;
    }
    #input-bar:focus-within {
        border-top: solid #7c3aed;
    }
    #input-prompt {
        color: #7c3aed;
        padding: 0 1;
        text-style: bold;
    }
    Input {
        background: transparent;
        border: none;
        width: 100%;
        color: #f8fafc;
    }
    #sidebar {
        width: 35;
        height: 100%;
        background: #0f172a;
        border-left: solid #1e293b;
        padding: 1 2;
    }
    .sidebar-title {
        text-style: bold;
        color: #38bdf8;
        margin-top: 1;
        margin-bottom: 0;
    }
    .sidebar-lbl {
        color: #94a3b8;
        margin-left: 1;
    }
    #lbl-quota {
        height: auto;
        padding: 0 1;
    }
    #lbl-connections {
        height: auto;
    }
    #recommend-container {
        margin-top: 1;
        padding: 1;
        background: #1e1b4b;
        border: tall #6366f1;
        height: auto;
    }
    #lbl-recommend {
        color: #e0e7ff;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "종료(Quit)", show=True),
        Binding("/", "focus_input_with_slash", "명령어(/)", show=True),
        Binding("escape", "hide_palette", "Close Palette", show=False),
        Binding("ctrl+l", "clear_chat", "채팅삭제(Clear)", show=True),
        Binding("f1", "show_help", "도움말(Help)", show=True),
    ]

    COMMAND_LIST = [
        ("/intent", "분석 계획 수립", "intent"),
        ("/analyze", "데이터 심층 분석", "analyze"),
        ("/explore", "데이터 탐색", "explore"),
        ("/connect", "소스 연결", "connect"),
        ("/project", "프로젝트 전환", "project"),
        ("/login", "LLM 인증", "login"),
        ("/report", "리포트 생성", "report"),
        ("/help", "도움말", "help"),
        ("/errors", "시스템 에러 로그", "errors"),
        ("/quit", "앱 종료", "quit"),
        ("/exit", "앱 종료", "exit"),
    ]


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_project = "default"
        self._init_orchestrator(self.current_project)
        self.palette_visible = False

        # Initialize command history
        self.command_history = CommandHistory()
        logger.info(f"Command history initialized with {len(self.command_history.entries)} entries")

    def on_exception(self, event) -> None:
        """Textual 프레임워크 레벨에서 발생하는 모든 예외를 캐치하여 로깅"""
        import traceback
        import sys
        from backend.utils.diagnostic_logger import diagnostic_logger
        
        error_msg = str(event.exception)
        exc_type = type(event.exception).__name__
        tb_str = "".join(traceback.format_exception(type(event.exception), event.exception, event.exception.__traceback__))
        
        # 1. diagnostic_logger에 기록
        try:
            diagnostic_logger.log_error(
                error_code="TEXTUAL_FRAMEWORK_ERROR",
                message=error_msg,
                context={
                    "exception_type": exc_type,
                    "traceback": tb_str
                }
            )
        except Exception as log_error:
            # 로깅 실패 시에도 계속 진행
            print(f"Failed to log to diagnostic_logger: {log_error}", file=sys.stderr)
        
        # 2. 콘솔 및 일반 로거에도 기록
        logger.error(f"\n{'='*80}\nTextual Framework Error: {exc_type}\n{'='*80}\n{tb_str}", exc_info=False)
        
        # 3. 에러를 textual_errors.log에도 별도 저장 (사용자가 쉽게 찾을 수 있도록)
        try:
            import pathlib
            project_root = pathlib.Path(__file__).parent.parent.parent
            error_log_path = project_root / "logs" / "textual_errors.log"
            
            with open(error_log_path, "a", encoding="utf-8") as f:
                import datetime
                f.write(f"\n\n{'='*80}\n")
                f.write(f"[{datetime.datetime.now().isoformat()}] {exc_type}: {error_msg}\n")
                f.write(f"{'='*80}\n")
                f.write(tb_str)
                f.write(f"\n{'='*80}\n")
        except Exception as file_error:
            print(f"Failed to write to textual_errors.log: {file_error}", file=sys.stderr)
        
        # 4. 사용자에게도 알림 (UI가 살아있다면)
        try:
            error_summary = f"[bold red]{exc_type}[/bold red]: {error_msg[:100]}"
            self.notify(
                f"⚠️ System Error Detected\n{error_summary}\n[dim]See logs/textual_errors.log or type /errors[/dim]",
                severity="error",
                timeout=15
            )
        except:
            pass

    def _init_orchestrator(self, project_id: str):
        try:
            from backend.orchestrator.collaborative_orchestrator import CollaborativeOrchestrator
            self.orchestrator = CollaborativeOrchestrator(project_id)
            self.conn_mgr = self.orchestrator.conn_mgr
            # Path Manager is already imported at top level
            self.registry_path = path_manager.get_project_path(project_id) / "connections.json"
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Horizontal(id="content-area"):
                with Vertical(id="chat-area"):
                    yield VerticalScroll(id="chat-log")
                    
                    with Vertical(id="input-bar"):
                        yield OptionList(id="command-menu")

                        with Horizontal(id="input-container"):
                            yield Label("❯", id="input-prompt")
                            yield Input(id="user-input", placeholder="Type a command or ask a question... (Type / to select)")
                
                with Vertical(id="sidebar"):
                    yield Label("PROJECT", classes="sidebar-title")
                    yield Label("• [dim]Loading...[/dim]", id="lbl-project", classes="sidebar-lbl")
                    
                    yield Label("INFRASTRUCTURE", classes="sidebar-title")
                    yield Label("• Auth: [yellow]Checking...[/yellow]", id="lbl-auth", classes="sidebar-lbl")
                    
                    yield Label("QUOTA (Daily Usage)", classes="sidebar-title")
                    yield Static("", id="lbl-quota", classes="sidebar-lbl")
                    
                    yield Label("ANALYSIS CONTEXT", classes="sidebar-title")
                    yield Label("• [dim]No active context[/dim]", id="lbl-context", classes="sidebar-lbl")
                    
                    yield Label("JOURNEY PROGRESS", classes="sidebar-title")
                    yield Static("", id="lbl-journey", classes="sidebar-lbl")
                    
                    yield Label("DATA SOURCES", classes="sidebar-title")
                    yield Static("[dim]Loading...[/dim]", id="lbl-connections", classes="sidebar-lbl")

                    yield Label("💡 ACTION RECOMMENDATION", classes="sidebar-title")
                    with Vertical(id="recommend-container"):
                        yield Static("Initializing...", id="lbl-recommend")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "BI-Agent Terminal"
        
        # 채팅 로그를 VerticalScroll로 가져오기
        chat_log = self.query_one("#chat-log", VerticalScroll)

        # 시스템 상태 체크
        is_auth = any(auth_manager.is_authenticated(p) for p in ["gemini", "claude", "openai"])
        status_color = "green" if is_auth else "yellow"
        status_text = "Ready" if is_auth else "Action Required (Auth)"
        
        if is_auth:
            context_manager.update_journey_step(1)
        
        # 환영 메시지 및 배너 표시
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        banner_art = (
            "\n"
            "[bold #7c3aed]   ╔═══════════════════════════════════════╗[/bold #7c3aed]\n"
            "[bold #7c3aed]   ║         ⚡ BI-AGENT TERMINAL          ║[/bold #7c3aed]\n"
            "[bold #7c3aed]   ║   Advanced Autonomous BI Co-pilot     ║[/bold #7c3aed]\n"
            "[bold #7c3aed]   ╚═══════════════════════════════════════╝[/bold #7c3aed]\n"
            "\n"
            f"[dim]System initialized at: {current_time}[/dim]\n"
            f"[dim]Status: [{status_color}]{status_text}[/{status_color}][/dim]\n"
            "\n"
            "[bold #38bdf8]🚀 BI ANALYSIS ROADMAP[/bold #38bdf8]\n"
            "1. [b]/login[/b]   - LLM 제공자 설정 (Gemini, Claude 등)\n"
            "2. [b]/connect[/b] - 데이터베이스 또는 데이터 파일 연결\n"
            "3. [b]/explore[/b] - 테이블 목록 탐색 및 분석 대상 선택\n"
            "4. [b]질문 입력[/b] - 궁금한 분석 내용을 자연어로 입력\n"
            "5. [b]/analyze[/b] - 심층 가설 수립 및 시각화 리포트 생성\n"
            "\n"
            "[dim]오른쪽 사이드바의 'ACTION RECOMMENDATION'이 다음단계를 안내합니다.[/dim]\n"
        )
        welcome_msg = MessageBubble(
            role="system",
            content=banner_art
        )
        chat_log.mount(welcome_msg)
        
        # 입력 필드에 자동 포커스
        self.set_focus(self.query_one("#user-input", Input))
        
        # 사이드바 초기 업데이트
        await self._update_sidebar()
        
        # HUD 초기 업데이트
        self._update_hud()
        
        logger.info("Terminal TUI mounted successfully.")

    async def _update_sidebar(self) -> None:
        """Update the sidebar status information."""
        try:
            # Project status
            project_lbl = self.query_one("#lbl-project", Label)
            current_project = os.environ.get("AG_PROJECT_ID", "default")
            project_lbl.update(f"• [cyan]{current_project}[/cyan]")

            # Auth status
            auth_lbl = self.query_one("#lbl-auth", Label)
            active_providers = []
            for p in ["gemini", "claude", "openai"]:
                if auth_manager.is_authenticated(p):
                    active_providers.append(p.capitalize())
            
            if active_providers:
                auth_lbl.update(f"• Auth: [green]✔ {', '.join(active_providers)}[/green]")
            else:
                auth_lbl.update("• Auth: [red]✘ Login Required[/red]")

            # Quota status - 시각화 향상
            quota_lbl = self.query_one("#lbl-quota", Static)
            quota_text = ""
            for p in ["gemini", "claude", "openai", "ollama"]:
                status = quota_manager.get_provider_status(p)
                usage = status.get('daily_count', 0)
                limit = status.get('limit', 1500)
                
                if limit != "∞" and isinstance(limit, int):
                    percent = min(100, int((usage / limit) * 100))
                    bar_len = 10
                    filled = int(percent / 100 * bar_len)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    
                    if percent < 50: color = "green"
                    elif percent < 80: color = "yellow"
                    else: color = "red"
                    
                    emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                    quota_text += f"{emoji} [{color}]{bar}[/{color}] {usage}/{limit}\n"
                else:
                    emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                    quota_text += f"{emoji} {p.capitalize()}: {usage}/∞\n"
            
            quota_lbl.update(quota_text.strip())

            # Analysis Context
            context_lbl = self.query_one("#lbl-context", Label)
            context_summary = context_manager.get_context_summary()
            if context_manager.active_table:
                context_lbl.update(f"• [cyan]{context_summary}[/cyan]")
            else:
                context_lbl.update("• [dim]No active context[/dim]")

            # Journey Progress
            journey_lbl = self.query_one("#lbl-journey", Static)
            steps = ["Launch", "Auth", "Conn", "Expl", "Pin", "Anlyz", "Rslt"]
            current_step = context_manager.journey_step
            
            journey_bar = ""
            for i, step_name in enumerate(steps):
                if i < current_step:
                    color = "green"
                    symbol = "✔"
                elif i == current_step:
                    color = "cyan"
                    symbol = "→"
                else:
                    color = "dim"
                    symbol = "○"
                journey_bar += f"[{color}]{symbol} {step_name}[/{color}]\n"
            journey_lbl.update(journey_bar.strip())

            # Connection status
            conn_lbl = self.query_one("#lbl-connections", Static)
            if os.path.exists(self.registry_path):
                try:
                    with open(self.registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                    if registry:
                        conn_lines = []
                        for name, info in registry.items():
                            c_type = info.get('type', 'unknown')
                            conn_lines.append(f"• {escape(str(name))} [dim]({escape(str(c_type))})[/dim]")
                        conn_lbl.update("\n".join(conn_lines))
                    else:
                        conn_lbl.update("[dim]No sources connected.[/dim]")
                except Exception as e:
                    logger.error(f"Error loading registry from {self.registry_path}: {e}")
                    conn_lbl.update("[red]Error loading registry[/red]")
            else:
                conn_lbl.update("[dim]No sources connected.[/dim]")
            # 6. Action Recommendation (New)
            recommend_lbl = self.query_one("#lbl-recommend", Static)
            recommendations = {
                0: "AI 설정을 위해 [b][cyan]/login[/cyan][/b]을 먼저 수행해 주세요.",
                1: "이제 데이터를 연결할 차례입니다. [b][cyan]/connect[/cyan][/b]를 입력하세요.",
                2: "데이터가 연결되었습니다! [b][cyan]/explore [conn_id][/cyan][/b]로 테이블을 확인하세요.",
                3: "테이블을 탐색 중입니다. 분석할 테이블을 [b][cyan]/explore [table][/cyan][/b]로 선택하세요.",
                4: "테이블이 선택되었습니다. 질문을 입력하거나 [b][cyan]/analyze[/cyan][/b]를 실행해 보세요!",
                5: "분석이 진행 중입니다. 결과를 기다려 주세요.",
                6: "분석 완료! 시각화 결과('v' 키)를 확인하거나 추가 질문을 던져보세요."
            }
            # Fallback if step is out of range
            tip = recommendations.get(current_step, recommendations[len(recommendations)-1])
            recommend_lbl.update(tip)

        except Exception as e:
            logger.error(f"Sidebar update failed: {e}")

        # Schedule next update
        self.set_timer(10, self._update_sidebar)
    
    def show_error_viewer(self):
        """최근 발생한 Textual 에러를 확인할 수 있는 화면 표시"""
        self.push_screen(ErrorViewerScreen())

    async def _update_hud(self) -> None:
        """현재 모델 및 컬텍스트 상태로 HUD 업데이트"""
        try:
            hud = self.query_one("#hud-status", HUDStatusLine)
            
            # 현재 모델 확인 (가장 먼저 인증된 모델)
            if auth_manager.is_authenticated("gemini"):
                hud.update_model("Gemini 2.0 Flash")
            elif auth_manager.is_authenticated("claude"):
                hud.update_model("Claude 3.5 Sonnet")
            elif auth_manager.is_authenticated("openai"):
                hud.update_model("GPT-4o")
            else:
                hud.update_model("Ollama")
            
            # 컬텍스트 사용률 시뮬레이션 (실제로는 LLM API에서 가져와야 함)
            # 여기서는 예시로 20%로 설정
            hud.update_context(20.0)
            
            # 10초마다 업데이트
            self.set_timer(10, self._update_hud)
        except Exception as e:
            logger.error(f"Error updating HUD: {e}")

    def _update_command_menu(self, filter_text: str = ""):
        """현재 입력값에 따라 명령 메뉴 항목을 필터링하여 업데이트"""
        menu = self.query_one("#command-menu", OptionList)
        menu.clear_options()
        
        # 슬래시 제거 후 소문자로 비교
        search_term = filter_text.lstrip("/").lower()
        
        matches_found = 0
        for cmd, desc, cmd_id in self.COMMAND_LIST:
            if not search_term or cmd.lstrip("/").startswith(search_term):
                menu.add_option(Option(f"{cmd:<10} [dim]{desc}[/dim]", id=cmd_id))
                matches_found += 1
        
        if matches_found > 0:
            menu.add_class("visible")
            self.palette_visible = True
            menu.highlighted = 0
        else:
            menu.remove_class("visible")
            self.palette_visible = False

    def on_input_changed(self, event: Input.Changed) -> None:
        """입력 변경 시 실시간 필터링 및 히스토리 내비게이션 초기화"""
        if event.value.startswith("/"):
            self._update_command_menu(event.value)
        else:
            menu = self.query_one("#command-menu", OptionList)
            menu.remove_class("visible")
            self.palette_visible = False

        if event.value:
            self.command_history.reset_navigation()

    def on_key(self, event) -> None:
        """Handle global keys for menu navigation, Tab autocomplete, and history navigation."""
        # '/' 키를 누르고 포커스가 입력창에 없으면 포커스 이동
        if (event.key == "/" or event.key == "slash" or event.key == "forward_slash"):
            user_input = self.query_one("#user-input", Input)
            if not user_input.has_focus:
                self.action_focus_input_with_slash()
                event.prevent_default()
                event.stop()
                return

        menu = self.query_one("#command-menu", OptionList)
        user_input = self.query_one("#user-input", Input)

        # === HISTORY NAVIGATION (Up/Down arrows when NOT in palette mode) ===
        if user_input.has_focus and not self.palette_visible:
            if event.key == "up":
                # Navigate to previous command
                prev_cmd = self.command_history.get_previous()
                if prev_cmd is not None:
                    user_input.value = prev_cmd
                    user_input.cursor_position = len(user_input.value)
                    event.prevent_default()
                    return
            elif event.key == "down":
                # Navigate to next command
                next_cmd = self.command_history.get_next()
                if next_cmd is not None:
                    user_input.value = next_cmd
                    user_input.cursor_position = len(user_input.value)
                    event.prevent_default()
                    return

        # === TAB COMPLETION ===
        if event.key == "tab" and user_input.has_focus:
            current_text = user_input.value.strip()

            # 1. Palette가 열려있으면 하이라이트된 항목으로 즉시 완성
            if self.palette_visible:
                ol = self.query_one("#command-menu", OptionList)
                if ol.highlighted is not None:
                    opt = ol.get_option_at_index(ol.highlighted)
                    matching_cmd = next((c[0] for c in self.COMMAND_LIST if c[2] == opt.id), None)
                    if matching_cmd:
                        user_input.value = matching_cmd
                        user_input.cursor_position = len(user_input.value)
                        ol.remove_class("visible")
                        self.palette_visible = False
                        event.prevent_default()
                        return

            # 2. 슬래시 명령어 자동 완성 (Palette가 닫혀있을 때)
            if current_text.startswith("/") or (current_text and not current_text.startswith("/") and len(current_text) >= 1):
                raw_prefix = current_text.lstrip("/")
                matches = [c[0] for c in self.COMMAND_LIST if c[0].lstrip("/").startswith(raw_prefix)]

                if len(matches) == 1:
                    user_input.value = matches[0]
                    user_input.cursor_position = len(user_input.value)
                    event.prevent_default()
                    return
                elif len(matches) > 1:
                    # Common prefix completion
                    common = matches[0].lstrip("/")
                    for m in matches[1:]:
                        while not m.lstrip("/").startswith(common):
                            common = common[:-1]
                    if len(common) > len(raw_prefix):
                        user_input.value = "/" + common
                        user_input.cursor_position = len(user_input.value)
                        event.prevent_default()
                        return

            # Tab completion for Korean BI phrases and history
            else:
                suggestions = self.command_history.get_suggestions(current_text)

                if len(suggestions) == 1:
                    # Single suggestion - autocomplete
                    user_input.value = suggestions[0]
                    user_input.cursor_position = len(user_input.value)
                elif len(suggestions) > 1:
                    # Multiple suggestions - complete to common prefix
                    common = suggestions[0]
                    for s in suggestions[1:]:
                        # Find common prefix
                        for i, (c1, c2) in enumerate(zip(common, s)):
                            if c1 != c2:
                                common = common[:i]
                                break
                        else:
                            # One is prefix of the other
                            common = common[:min(len(common), len(s))]

                    if len(common) > len(current_text):
                        user_input.value = common
                        user_input.cursor_position = len(user_input.value)
                    else:
                        # Show suggestions in notification
                        suggestion_text = ", ".join(suggestions[:5])
                        if len(suggestions) > 5:
                            suggestion_text += f"... (+{len(suggestions) - 5} more)"
                        self.notify(f"Suggestions: {suggestion_text}", timeout=3)

                event.prevent_default()
                return

        # === PALETTE MENU NAVIGATION ===
        if self.palette_visible and user_input.has_focus:
            if event.key == "escape":
                menu.remove_class("visible")
                self.palette_visible = False
                event.prevent_default()
            elif event.key == "up":
                # Navigate menu items upward
                if menu.highlighted is not None and menu.highlighted > 0:
                    menu.highlighted -= 1
                event.prevent_default()
            elif event.key == "down":
                # Navigate menu items downward
                if menu.highlighted is not None and menu.highlighted < menu.option_count - 1:
                    menu.highlighted += 1
                event.prevent_default()
            elif event.key == "enter":
                # Execute selected menu item
                if menu.highlighted is not None:
                    option = menu.get_option_at_index(menu.highlighted)
                    if option and option.id:
                        command_map = {
                            "intent": "/intent",
                            "analyze": "/analyze",
                            "explore": "/explore",
                            "connect": "/connect",
                            "project": "/project",
                            "login": "/login",
                            "help": "/help"
                        }
                        cmd = command_map.get(option.id, "/" + option.id)
                        user_input.value = ""
                        menu.remove_class("visible")
                        self.palette_visible = False
                        import asyncio
                        asyncio.create_task(self.handle_command(cmd))
                        event.prevent_default()

    def action_hide_palette(self) -> None:
        """Force hide the menu."""
        menu = self.query_one("#command-menu", OptionList)
        menu.remove_class("visible")
        self.palette_visible = False
        self.query_one("#user-input", Input).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command palette selection with Enter key"""
        # 명령 메뉴 이벤트가 아닌 경우(예: AuthScreen의 OptionList) 무시
        if event.option_list.id != "command-menu":
            return
            
        import asyncio
        palette = self.query_one("#command-menu", OptionList)
        palette.remove_class("visible")
        self.palette_visible = False
        
        # 선택된 명령어를 입력 필드에 설정
        command_id = event.option.id
        if command_id:
            user_input = self.query_one("#user-input", Input)
            
            # 명령어 매핑
            command_map = {
                "intent": "/intent",
                "analyze": "/analyze",
                "explore": "/explore",
                "connect": "/connect",
                "project": "/project",
                "login": "/login",
                "report": "/report",
                "help": "/help"
            }
            
            cmd = command_map.get(command_id, "/" + command_id)
            user_input.value = cmd
            
            # 입력으로 포커스 복귀 및 명령 실행
            user_input.focus()
            # Enter를 누른 것처럼 실행
            asyncio.create_task(self.handle_command(cmd))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle final input execution."""
        user_text = event.value.strip()
        if not user_text:
            return

        chat_log = self.query_one("#chat-log", VerticalScroll)

        # Save to command history
        context = "slash_command" if user_text.startswith("/") else "query"
        self.command_history.add_command(user_text, context=context)
        logger.debug(f"Command saved to history: {user_text[:50]}...")

        # 사용자 메시지 추가
        user_msg = MessageBubble(role="user", content=user_text)
        chat_log.mount(user_msg)
        chat_log.scroll_end(animate=False)

        self.query_one("#user-input", Input).value = ""

        # 크래시 방지: 제거된 HUD 참조 제거
        # (기존 hud = self.query_one("#hud-status") 부분 삭제)

        if user_text.startswith("/"):
            await self.handle_command(user_text)
        else:
            await self.process_query(user_text)

    async def handle_command(self, cmd_text: str):
        """Routing for slash commands."""
        parts = cmd_text.split()
        cmd = parts[0]
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        if cmd == "/intent" or cmd == "/analyze":
            user_intent = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not user_intent:
                msg = MessageBubble(role="system", content="[yellow]분석 의도를 입력해주세요. 예: /analyze 이번 달 매출 하락 원인 분석[/yellow]")
                chat_log.mount(msg)
            else:
                asyncio.create_task(self._handle_analyze_command(user_intent))
                
        elif cmd == "/connect":
            def on_connected(conn_id: str):
                if conn_id:
                    # 비동기 워커로 스캔 실행 (UI 프리징 방지)
                    self.run_worker(self._run_scan(conn_id))
            
            self.push_screen(ConnectionScreen(callback=on_connected))
        elif cmd == "/project":
            self.action_switch_project()
        elif cmd == "/login":
            self.push_screen(AuthScreen())
        elif cmd == "/explore":
            args = parts[1:]
            query = args[0] if args else None
            msg = MessageBubble(role="system", content="[dim]데이터 구조를 탐색 중입니다...[/dim]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            self.run_worker(self._run_explore(query))
        elif cmd == "/errors":
            self.show_error_viewer()
        elif cmd == "/help":
            help_content = (
                "[bold cyan]◈ BI-Agent 사용 가이드 ◈[/bold cyan]\n\n"
                "[bold #38bdf8]명령어 일람:[/bold #38bdf8]\n"
                "• [b]/login[/b]   - LLM API 키 설정 (AI 활성화 핵심)\n"
                "• [b]/connect[/b] - DB/File 연결 (sqlite, postgres, excel)\n"
                "• [b]/explore[/b] - 테이블 목록 및 상세 스키마 탐색\n"
                "• [b]/analyze[/b] - 자연어 질문 기반 데이터 분석 및 시각화\n"
                "• [b]/errors[/b]  - 시스템 장애 및 로직 에러 로그 확인\n"
                "• [b]/quit[/b] 또는 [b]/exit[/b] - 앱 종료\n\n"
                "[bold #38bdf8]단축키 가이드:[/bold #38bdf8]\n"
                "• [b]/[/b] : 명령어 입력 시작 (입력창 포커스 + / 자동입력) ⭐\n"
                "• [b]q[/b] : 앱 종료\n"
                "• [b]v[/b] : 분석 시각화 리포트/차트 보기\n"
                "• [b]F1[/b] : 도움말 보기\n"
                "• [b]ctrl+l[/b] : 채팅 내용 삭제\n"
                "• [b]tab[/b] : 명령어 자동 완성 및 입력 보조\n"
                "• [b]ctrl+e[/b] : 에러 로그 창 열기\n\n"
                "[dim]Tip: 오른쪽 사이드바의 'ACTION RECOMMENDATION'에서 항상 다음 단계를 확인하세요![/dim]"
            )
            msg = MessageBubble(role="system", content=help_content)
            chat_log.mount(msg)
        elif cmd in ["/quit", "/exit"]:
            await self.action_quit()
        else:
            msg = MessageBubble(role="system", content=f"[red]알 수 없는 명령어입니다: {cmd}[/red]")
            chat_log.mount(msg)
        
        chat_log.scroll_end(animate=False)

    async def process_query(self, query: str):
        """Handle natural language queries."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        thinking_msg = MessageBubble(role="system", content="[dim]분석 에이전트가 사고하는 중...[/dim]")
        chat_log.mount(thinking_msg)
        chat_log.scroll_end(animate=False)
        
        try:
            # Check for active connection
            if not os.path.exists(self.conn_mgr.registry_path):
                 msg = MessageBubble(role="system", content="[yellow]연결된 데이터 소스가 없습니다. /connect 를 입력해 소스를 추가해 주세요.[/yellow]")
                 chat_log.mount(msg)
                 return

            # Execute via worker to keep UI alive
            self.run_worker(self._run_analysis(query))
        except Exception as e:
            msg = MessageBubble(role="system", content=f"[bold red]Error:[/bold red] {e}")
            chat_log.mount(msg)

    async def _run_analysis(self, query: str):
        # Implementation depends on orchestrator.run
        pass

    async def _run_explore(self, target: Optional[str] = None):
        """Explore metadata: connections -> tables -> schema."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        try:
            from backend.agents.data_source.metadata_scanner import MetadataScanner
            scanner = MetadataScanner(self.conn_mgr)

            if not target:
                # 1. List connections
                if not os.path.exists(self.conn_mgr.registry_path):
                    content = "[yellow]연결된 데이터 소스가 없습니다. /connect 명령어로 추가해 주세요.[/yellow]"
                else:
                    with open(self.conn_mgr.registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                    if not registry:
                        content = "[yellow]연결된 데이터 소스가 없습니다.[/yellow]"
                    else:
                        content = "[bold cyan]Connected Data Sources:[/bold cyan]\n"
                        for cid, info in registry.items():
                            content += f"• [b]{cid}[/b] ([dim]{info['type']}[/dim])\n"
                        content += "\n[dim]Tip: '/explore <conn_id>'를 입력하여 테이블 목록을 확인하세요.[/dim]"
                chat_log.mount(MessageBubble(role="system", content=content))
            
            elif "." in target:
                # 2. List columns (schema) for a table: <conn_id>.<table_name>
                conn_id, table_name = target.split(".", 1)
                chat_log.mount(MessageBubble(role="system", content=f"[dim]'{conn_id}'의 '{table_name}' 테이블 스키마를 조회 중...[/dim]"))
                
                # Fetch metadata
                meta = await asyncio.get_event_loop().run_in_executor(None, scanner.scan_table, conn_id, table_name)
                
                # Context Management: Pin this table as active context
                context_manager.set_active_table(conn_id, table_name, meta)
                await self._update_sidebar()
                
                content = f"[bold cyan]Table: {table_name}[/bold cyan] ([dim]Source: {conn_id}[/dim])\n"
                content += f"📊 Estimated Rows: {meta.get('row_count_estimate', 'Unknown')}\n\n"
                content += "[bold]Columns:[/bold]\n"
                
                cols = meta.get("columns", {})
                for col_name, col_info in cols.items():
                    dtype = col_info.get("type", "unknown")
                    missing = col_info.get("missing_ratio", 0) * 100
                    content += f"• [b]{col_name}[/b] ([green]{dtype}[/green]) [dim]| Missing: {missing:.1f}%[/dim]\n"
                
                chat_log.mount(MessageBubble(role="system", content=content))
                chat_log.mount(MessageBubble(role="system", content=f"[green]📌 '{table_name}' 테이블이 분석 컨텍스트로 고정되었습니다. 이제 바로 분석 질문을 던질 수 있습니다.[/green]"))

            else:
                # 3. List tables for a connection: <conn_id>
                conn_id = target
                chat_log.mount(MessageBubble(role="system", content=f"[dim]'{conn_id}'의 테이블 목록을 조회 중...[/dim]"))
                
                # Using scanner's internal _list_tables via scan_source or direct call
                # scan_source is heavier but safer
                metadata = await asyncio.get_event_loop().run_in_executor(None, scanner.scan_source, conn_id)
                tables = metadata.get("tables", [])
                
                if not tables:
                    content = f"[yellow]'{conn_id}'에 발견된 테이블이 없습니다.[/yellow]"
                else:
                    content = f"[bold cyan]Tables in '{conn_id}':[/bold cyan]\n"
                    for t in tables:
                        tname = t["table_name"]
                        rows = t.get("row_count_estimate", "?")
                        content += f"• [b]{tname}[/b] ([dim]{rows} rows[/dim])\n"
                    content += f"\n[dim]Tip: '/explore {conn_id}.<table_name>'를 입력하여 상세 스키마를 확인하세요.[/dim]"
                
                chat_log.mount(MessageBubble(role="system", content=content))
                
                # Journey Progress: Update to Explore step
                context_manager.update_journey_step(3)
                await self._update_sidebar()

        except Exception as e:
            logger.error(f"Explore failed: {e}")
            chat_log.mount(MessageBubble(role="system", content=f"[bold red]Explore Error:[/bold red] {e}"))
        
        chat_log.scroll_end(animate=False)

    async def _run_scan(self, conn_id: str):
        """Perform scan after connection and update sidebar."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        try:
            chat_log.mount(MessageBubble(role="system", content=f"[bold blue]Scanning data source '{conn_id}'...[/bold blue]"))
            chat_log.scroll_end(animate=False)
            
            from backend.agents.data_source.metadata_scanner import MetadataScanner
            scanner = MetadataScanner(self.conn_mgr)
            
            # Run scan in executor
            meta = await asyncio.get_event_loop().run_in_executor(None, scanner.scan_source, conn_id)
            
            table_count = len(meta.get("tables", []))
            summary = f"[green]✅ '{conn_id}' 연결 및 스캔 완료![/green]\n📊 발견된 테이블 수: {table_count}\n[dim]Tip: '/explore {conn_id}' 을 입력하여 목록을 확인하세요.[/dim]"
            
            chat_log.mount(MessageBubble(role="system", content=summary))
            
            # Journey Progress: Update to Connect step
            context_manager.update_journey_step(2) # Connect
            await self._update_sidebar() # Update sidebar to show new source and journey progress
        except Exception as e:
            logger.error(f"Scan failed for {conn_id}: {e}")
            error_msg = f"[bold red]Scan Error:[/bold red] {e}"
            if "timeout" in str(e).lower() or "Operation timed out" in str(e):
                error_msg += "\n\n[yellow]💡 팁: 연결 시간이 초과되었습니다. VPN 연결 상태를 확인하거나, DB 서버가 활성화되어 있는지 확인해 보세요.[/yellow]"
            chat_log.mount(MessageBubble(role="system", content=error_msg))
        
        chat_log.scroll_end(animate=False)

    def show_response(self, response: str):
        chat_log = self.query_one("#chat-log", VerticalScroll)
        agent_msg = MessageBubble(role="agent", content=response)
        chat_log.mount(agent_msg)
        chat_log.scroll_end(animate=False)

    async def action_show_visuals(self, data: Dict[str, Any], title: str = "Analysis Insights") -> None:
        """분석 결과 시각화 스크린 표시"""
        self.push_screen(VisualAnalysisScreen(data, title))

    async def _handle_analyze_command(self, query: str):
        """/analyze 명령어 처리 고도화"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        if not context_manager.active_table:
            chat_log.mount(MessageBubble(role="system", content="[yellow]⚠️ 먼저 분석할 테이블을 선택(/explore)해 주세요.[/yellow]"))
            return

        chat_log.mount(MessageBubble(role="system", content=f"🚀 '{context_manager.active_table}' 테이블 기반 분석을 시작합니다..."))
        
        try:
            # 1. Intent Analysis & Plan
            plan_data = await self.orchestrator.handle_intent(query, context_manager.active_conn_id)
            
            if plan_data.get("status") == "error":
                chat_log.mount(MessageBubble(role="system", content=f"[red]분석 실패: {plan_data.get('message')}[/red]"))
                return
                
            # Plan 출력
            plan_msg = f"[bold cyan]Analysis Plan:[/bold cyan]\n"
            for i, step in enumerate(plan_data.get("steps", [])):
                plan_msg += f"{i+1}. {step}\n"
            plan_msg += f"\n[dim]Value: {plan_data.get('estimated_value', '')}[/dim]"
            chat_log.mount(MessageBubble(role="agent", content=plan_msg))

            # 2. Complete Analysis
            result = await self.orchestrator.handle_complex_request(query, context_manager.active_conn_id)
            
            if result.get("status") == "error":
                chat_log.mount(MessageBubble(role="system", content=f"[red]분석 중 오류 발생: {result.get('message')}[/red]"))
                return

            chat_log.mount(MessageBubble(role="agent", content=f"✅ 분석 완료! 시각화 리포트를 생성했습니다.\n[dim]결과 파일: {result.get('output_file')}[/dim]"))
            
            # 3. Show Visuals
            tui_data = result.get("tui_data", {"metrics": [], "charts": []})
            self.push_screen(VisualAnalysisScreen(tui_data, title=f"Analysis: {context_manager.active_table}"))
            
            # 4. Success message in Chat
            chat_log.mount(MessageBubble(role="system", content="[green]💡 'v' 키를 누르면 언제든지 시각화 리포트를 다시 볼 수 있습니다.[/green]"))
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            chat_log.mount(MessageBubble(role="system", content=f"[red]분석 중 예외 발생: {str(e)}[/red]"))
        
        chat_log.scroll_end(animate=False)

    def action_clear_chat(self) -> None:
        chat_log = self.query_one("#chat-log", VerticalScroll)
        # 모든 자식 제거
        chat_log.remove_children()
        # 환영 메시지 다시 추가
        welcome_msg = MessageBubble(
            role="system",
            content=(
                "[bold cyan]어서오세요! BI-Agent Entrance Hall입니다[/bold cyan]\n"
                "분석가의 생산성을 3배 이상 높이는 지능형 조수입니다.\n\n"
                "[dim]명령어: /help 로 시작하거나 질문을 입력하세요.[/dim]"
            )
        )
        chat_log.mount(welcome_msg)

    def action_switch_project(self) -> None:
        def set_project(project_name: str) -> None:
            if project_name:
                # 프로젝트 전환 메시지
                chat_log = self.query_one("#chat-log", VerticalScroll)
                msg = MessageBubble(
                    role="system",
                    content=f"[green]Project switched to '{project_name}'.[/green]"
                )
                chat_log.mount(msg)
                chat_log.scroll_end(animate=False)

        self.push_screen(ProjectScreen(self.current_project), set_project)

    async def action_quit(self) -> None:
        try:
            self.conn_mgr.close_all()
        except: pass
        self.exit()

    def action_focus_input(self) -> None:
        """입력창에 포커스"""
        try:
            self.query_one("#user-input", Input).focus()
        except Exception:
            pass

    def action_focus_input_with_slash(self) -> None:
        """입력창에 포커스하고 '/' 입력"""
        try:
            input_widget = self.query_one("#user-input", Input)
            # 이미 포커스가 있고 내용이 있으면 그냥 pass (입력 중간에 / 입력 방지)
            if input_widget.has_focus and input_widget.value:
                return
            input_widget.focus()
            if not input_widget.value:
                input_widget.value = "/"
                input_widget.cursor_position = 1
        except Exception:
            pass

    async def action_show_help(self) -> None:
        """도움말 표시"""
        await self._run_help()

def run_app():
    from backend.utils.pre_flight import run_pre_flight
    
    # Phase 0: Pre-flight Check (TUI 진입 전 선행 검사)
    try:
        if not run_pre_flight():
            # 의존성이나 인증이 안되었을 때 종료할지 여부는 checker에서 결정했으나,
            # 최소한 발자국은 남김
            pass
    except Exception as e:
        print(f"Pre-flight check failed: {e}")

    try:
        app = BI_AgentConsole()
        app.run()
    except Exception as e:
        logger.critical(f"App crashed on startup: {e}")
        print(f"CRITICAL ERROR: {e}\nCheck logs/tui.log for details.")

if __name__ == "__main__":
    run_app()
