from textual.screen import ModalScreen
from backend.orchestrator.auth_manager import auth_manager

class AuthScreen(ModalScreen):
    """
    환영 메시지와 함께 API 키 설정을 유도하는 모달 스크린
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="auth-modal"):
            yield Label("[bold white]Welcome to BI-Agent[/bold white]\n", id="auth-title")
            yield Label("이 에이전트를 사용하려면 Google Gemini API 키가 필요합니다.\n")
            yield Label("[dim]아래 'Login with Google'을 눌러 API 키를 발급받으세요.[/dim]\n")
            yield Horizontal(id="auth-buttons"):
                yield Static("[bold green] 1. Login with Google [/bold green]", id="btn-login")
                yield Static("  [dim]|[/dim]  ")
                yield Static("[bold blue] 2. I have a key [/bold blue]", id="btn-input")
            yield Input(id="key-input", placeholder="Enter your API Key here...", password=True)
            yield Label("\n[dim]키를 입력하고 Enter를 누르면 설정이 보존됩니다.[/dim]")
    
    CSS = """
    #auth-modal {
        width: 60;
        height: 25;
        background: #1e293b;
        border: thick #38bdf8;
        padding: 2;
        align: center middle;
    }
    #auth-title {
        font-size: 150%;
        text-align: center;
    }
    #auth-buttons {
        height: 3;
        align: center middle;
        margin: 1;
    }
    #key-input {
        display: none;
        border: solid #38bdf8;
    }
    #key-input.visible {
        display: block;
    }
    """

    async def on_click(self, event) -> None:
        if event.node.id == "btn-login":
            await auth_manager.login_with_google()
            self.query_one("#key-input", Input).add_class("visible")
            self.query_one("#key-input", Input).focus()
        elif event.node.id == "btn-input":
            self.query_one("#key-input", Input).add_class("visible")
            self.query_one("#key-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if key:
            auth_manager.set_gemini_key(key)
            self.dismiss(True)

class BI_AgentConsole(App):
    """
    A premium TUI for BI-Agent that acts as a supplementary tool
    without the need for a separate web server.
    """
    CSS = """
    Screen {
        background: #0f172a;
    }
    #sidebar {
        width: 25%;
        background: #1e293b;
        border-right: tall #334155;
        padding: 1;
    }
    #main-content {
        width: 75%;
    }
    #chat-area {
        height: 65%;
        border-bottom: tall #334155;
        padding: 1;
        overflow-y: scroll;
    }
    #preview-area {
        height: 35%;
        padding: 1;
        background: #111827;
    }
    Input {
        dock: bottom;
        margin: 1;
        border: solid #38bdf8;
    }
    Log, RichLog {
        height: 100%;
        background: transparent;
    }
    #wizard-options {
        display: none;
        height: 10;
        border: double #38bdf8;
        background: #1e293b;
        margin: 1;
    }
    #wizard-options.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_connection", "Add Connection", show=True),
        Binding("e", "edit_connection", "Edit Selected", show=True),
        Binding("delete", "delete_connection", "Delete Selected", show=True),
        Binding("r", "refresh", "Refresh Sources", show=True),
        Binding("s", "save", "Save Last JSON", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.registry_path = "config/connections.json"
        self.orchestrator = CollaborativeOrchestrator(self.registry_path)
        self.conn_mgr = self.orchestrator.conn_mgr
        self.last_result = None
        # Wizard state
        self.wizard_step = 0
        self.wizard_data = {}
        self.wizard_mode = "add" # "add" or "edit"
        self.target_conn_id = None
        self.conn_map = {} # Map index to conn_id

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[bold cyan]Linked Sources[/bold cyan]")
                yield ListView(id="source-list")
                yield Label("\n[dim][b]A[/b]:Add [b]E[/b]:Edit [b]Del[/b]:Delete[/dim]")
            with Vertical(id="main-content"):
                with Vertical(id="chat-area"):
                    yield RichLog(id="chat-log", markup=True, wrap=True)
                    yield OptionList(id="wizard-options")
                with Vertical(id="preview-area"):
                    yield Static(id="preview-content")
        yield Input(id="user-input", placeholder="Ask anything... or manage sources on the left")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "BI-Agent Premium Console"
        self.sub_title = "Supplementary Analytics Assistant v1.0"
        
        # Check Authentication
        if not auth_manager.is_authenticated():
            self.push_screen(AuthScreen())

        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("안녕하세요! [bold blue]BI-Agent Console[/bold blue]입니다.")
        chat_log.write("사이드바에서 소스를 선택하고 [bold]E[/bold]나 [bold]Del[/bold]을 눌러 관리해 보세요.\n")
        self.action_refresh()

    def action_refresh(self) -> None:
        """Reloads the connection list from the registry."""
        source_list = self.query_one("#source-list", ListView)
        source_list.clear()
        self.conn_map = {}
        
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)
            for idx, (conn_id, info) in enumerate(registry.items()):
                icon = "🌐" if info.get("category") == "Cloud" else "📂"
                source_list.append(ListItem(Label(f"{icon} {info['name']} ({conn_id})")))
                self.conn_map[idx] = conn_id
        else:
            source_list.append(ListItem(Label("[dim]No sources registered[/dim]")))

    def get_selected_conn_id(self) -> str:
        source_list = self.query_one("#source-list", ListView)
        if source_list.index is not None and source_list.index in self.conn_map:
            return self.conn_map[source_list.index]
        return None

    def action_add_connection(self) -> None:
        """Starts the connection wizard in ADD mode."""
        self.wizard_mode = "add"
        self.wizard_step = 1
        self.wizard_data = {}
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(Panel("[bold magenta]🧙 CONNECTION WIZARD: ADD[/bold magenta]", border_style="magenta"))
        chat_log.write("[bold cyan]Step 1: 소스 타입 선택[/bold cyan] (화살표 키로 이동, Enter로 선택)")
        
        # Show OptionList
        opt_list = self.query_one("#wizard-options", OptionList)
        opt_list.clear_options()
        opt_list.add_options([
            Option("SQLite", id="sqlite"),
            Option("Excel", id="excel"),
            Option("PostgreSQL", id="postgres"),
            Option("MySQL", id="mysql")
        ])
        opt_list.add_class("visible")
        opt_list.focus()

    def action_edit_connection(self) -> None:
        """Starts the connection wizard in EDIT mode."""
        conn_id = self.get_selected_conn_id()
        if not conn_id:
            self.query_one("#chat-log", RichLog).write("[bold red]⚠ 오류:[/bold red] 수정할 소스를 먼저 선택해 주세요.")
            return

        self.wizard_mode = "edit"
        self.target_conn_id = conn_id
        self.wizard_step = 1
        self.wizard_data = {}
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(Panel(f"[bold yellow]🔧 CONNECTION WIZARD: EDIT ({conn_id})[/bold yellow]", border_style="yellow"))
        chat_log.write("[bold cyan]Step 1: 소스 타입 변경[/bold cyan] (화살표 키 선택)")
        
        opt_list = self.query_one("#wizard-options", OptionList)
        opt_list.clear_options()
        opt_list.add_options([Option("SQLite", id="sqlite"), Option("Excel", id="excel"), Option("PostgreSQL", id="postgres"), Option("MySQL", id="mysql")])
        opt_list.add_class("visible")
        opt_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handles type selection via arrow keys + Enter."""
        if self.wizard_step == 1:
            chat_log = self.query_one("#chat-log", RichLog)
            self.wizard_data["type"] = event.option.id
            self.wizard_step = 2
            
            # Hide OptionList
            opt_list = self.query_one("#wizard-options", OptionList)
            opt_list.remove_class("visible")
            
            chat_log.write(f" [green]▶ Selected Type:[/green] {self.wizard_data['type'].upper()}")
            chat_log.write("[bold cyan]Step 2: 연결 이름 입력[/bold cyan]")
            self.query_one("#user-input", Input).focus()
            self.query_one("#user-input", Input).placeholder = "이름을 입력하세요"

    def action_delete_connection(self) -> None:
        """Triggers deletion confirmation."""
        conn_id = self.get_selected_conn_id()
        if not conn_id:
            return
        
        self.wizard_mode = "delete"
        self.target_conn_id = conn_id
        self.wizard_step = 99 # Special step for delete confirmation
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(Panel(f"[bold red]⚠ DELETE CONFIRMATION: {conn_id}[/bold red]", border_style="red"))
        chat_log.write(f"정말로 [bold]'{conn_id}'[/bold] 연결을 삭제하시겠습니까? (삭제하려면 'yes' 입력)")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_query = event.value.strip()
        if not user_query:
            return

        input_widget = self.query_one("#user-input", Input)
        chat_log = self.query_one("#chat-log", RichLog)

        # Clear standard analysis queries immediately
        # But for wizard, we might want to pre-fill the NEXT step's value
        if self.wizard_step == 0:
            input_widget.value = ""
        
        if self.wizard_step > 0:
            await self.handle_wizard_step(user_query)
        else:
            await self.process_analysis_query(user_query)
        
        # In wizard mode, handle_wizard_step might have set a template.
        # If it didn't, and we're just finishing a step, clear it.
        if self.wizard_step == 0:
            input_widget.value = ""
        elif self.wizard_step == 2: # After selecting type, clear for name input
            input_widget.value = ""

    async def handle_wizard_step(self, value: str) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        input_widget = self.query_one("#user-input", Input)

        # Deletion Confirmation
        if self.wizard_step == 99:
            if value.lower() == "yes":
                try:
                    with open(self.registry_path, 'r') as f:
                        registry = json.load(f)
                    if self.target_conn_id in registry:
                        del registry[self.target_conn_id]
                        with open(self.registry_path, 'w') as f:
                            json.dump(registry, f, indent=2)
                        chat_log.write(f"\n[bold green]🗑 연결 '{self.target_conn_id}'이(가) 삭제되었습니다.[/bold green]")
                        self.action_refresh()
                except Exception as e:
                    chat_log.write(f"\n[bold red]❌ 삭제 실패:[/bold red] {str(e)}")
            else:
                chat_log.write("\n[yellow]삭제가 취소되었습니다.[/yellow]")
            self.wizard_step = 0
            return

        # Step 1: Managed via OptionList (this method handles text input if needed, but we skip)
        if self.wizard_step == 1:
            return 
        
        # Step 2: Name Input
        elif self.wizard_step == 2:
            self.wizard_data["name"] = value
            self.wizard_step = 3
            chat_log.write(f" [green]▶ Name:[/green] {value}")
            chat_log.write("[bold cyan]Step 3: 설정 정보 입력[/bold cyan]")
            
            # Provide Template based on type
            templates = {
                "sqlite": "backend/data/sample_sales.sqlite",
                "excel": "path/to/data.xlsx",
                "postgres": "host=localhost port=5432 dbname=postgres user=postgres password=secret",
                "mysql": "host=localhost port=3306 dbname=mysql user=root password=secret"
            }
            template = templates.get(self.wizard_data["type"], "")
            chat_log.write(f" [dim]Template: {template}[/dim]")
            chat_log.write(" [italic blue]* 아래 입력창의 템플릿을 수정하여 입력하세요.[/italic blue]")
            
            input_widget.value = template
            input_widget.focus()

        # Step 3: Config Input & Finalization
        elif self.wizard_step == 3:
            config_input = value
            if os.path.isfile(config_input):
                try:
                    if config_input.endswith('.json'):
                        with open(config_input, 'r') as f:
                            self.wizard_data["config"] = json.load(f)
                    else:
                        self.wizard_data["config"] = {"path": config_input} 
                except Exception as e:
                    chat_log.write(f" [red]⚠ 파일 로드 실패:[/red] {str(e)}")
                    return
            else:
                if self.wizard_data["type"] in ["sqlite", "excel"]:
                    self.wizard_data["config"] = {"path": config_input}
                else:
                    self.wizard_data["config"] = config_input

            # Finalize (Add or Update)
            conn_id = self.target_conn_id if self.wizard_mode == "edit" else f"conn_{int(os.path.getmtime(self.registry_path) if os.path.exists(self.registry_path) else 1)}"
            try:
                self.conn_mgr.register_connection(
                    conn_id=conn_id,
                    conn_type=self.wizard_data["type"],
                    config=self.wizard_data["config"],
                    name=self.wizard_data["name"]
                )
                msg = "수정" if self.wizard_mode == "edit" else "등록"
                chat_log.write(Panel(f"[bold green]✨ SUCCESS: 데이터 소스가 성공적으로 {msg}되었습니다![/bold green]", border_style="green"))
                self.action_refresh()
            except Exception as e:
                chat_log.write(f"\n[bold red]❌ 처리 실패:[/bold red] {str(e)}")
            
            self.wizard_step = 0
            self.wizard_mode = "add"
            input_widget.placeholder = "대화 분석 시작... 또는 사이드바 관리"

    async def process_analysis_query(self, user_query: str) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        preview = self.query_one("#preview-content", Static)

        chat_log.write(f"[bold green]YOU:[/bold green] {user_query}")
        
        try:
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)
            if not registry:
                chat_log.write("[bold red]ERROR:[/bold red] 등록된 데이터 소스가 없습니다. [b]A[/b]를 눌러 먼저 등록해 주세요.")
                return
            
            # 리스트 중 첫번째 혹은 질문과 가장 매칭되는 소스 선택 (여기선 단순화)
            conn_id = list(registry.keys())[0]
            chat_log.write(f"[bold blue]SYSTEM:[/bold blue] [cyan]'{registry[conn_id]['name']}'[/cyan] 소스에서 분석을 시작합니다...")
            
            result = self.orchestrator.handle_complex_request(user_query, conn_id)
            self.last_result = result
            
            chat_log.write(f"[bold blue]BI-Agent:[/bold blue] 분석 결과:")
            chat_log.write(f" > [dim]{result['reasoning']}[/dim]\n")
            
            with open(result["path"], "r") as f:
                meta_json = json.load(f)
            
            syntax = Syntax(json.dumps(meta_json, indent=2), "json", theme="monokai", line_numbers=True)
            preview.update(Panel(syntax, title=f"[bold yellow]Preview: {result['summary']['table']}[/bold yellow]", border_style="yellow"))

        except Exception as e:
            chat_log.write(f"[bold red]ERROR:[/bold red] {str(e)}")

    def action_clear_chat(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def action_save(self) -> None:
        if self.last_result:
            self.query_one("#chat-log", RichLog).write(f"\n[bold cyan]SYSTEM:[/bold cyan] JSON이 {self.last_result['path']}에 보존되었습니다.")

def run_app():
    app = BI_AgentConsole()
    app.run()

if __name__ == "__main__":
    run_app()
