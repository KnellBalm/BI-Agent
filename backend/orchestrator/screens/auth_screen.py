import json
import logging
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Input, OptionList, Button
from textual.widgets.option_list import Option
from textual.screen import ModalScreen

from backend.orchestrator.managers.auth_manager import auth_manager
from backend.orchestrator.managers.context_manager import context_manager
from backend.utils.path_config import path_manager

logger = logging.getLogger("tui")

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
            creds_path = path_manager.base_dir / "credentials.json"
            
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
            # sidebar update is handled by the app which calls this screen
            if hasattr(self.app, "_update_sidebar"):
                await self.app._update_sidebar()
            
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            self.notify(f"❌ API 키 저장 실패: {e}", severity="error")
