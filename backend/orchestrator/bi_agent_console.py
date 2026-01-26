from textual.screen import ModalScreen
from backend.orchestrator.auth_manager import auth_manager
from backend.utils.logger_setup import setup_logger

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

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
        try:
            if event.node.id == "btn-login":
                await auth_manager.login_with_google()
                self.query_one("#key-input", Input).add_class("visible")
                self.query_one("#key-input", Input).focus()
            elif event.node.id == "btn-input":
                self.query_one("#key-input", Input).add_class("visible")
                self.query_one("#key-input", Input).focus()
        except Exception as e:
            logger.error(f"Error in AuthScreen click: {e}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if key:
            auth_manager.set_gemini_key(key)
            self.dismiss(True)

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
        font-size: 150%;
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
        
        if not os.path.exists("projects"):
            os.makedirs("projects", exist_ok=True)
            
        projects = [d for d in os.listdir("projects") if os.path.isdir(os.path.join("projects", d))]
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
    #project-header {
        background: #064e3b;
        color: #ecfdf5;
        padding: 0 1;
        text-align: center;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_connection", "Add Connection", show=True),
        Binding("e", "edit_connection", "Edit Selected", show=True),
        Binding("delete", "delete_connection", "Delete Selected", show=True),
        Binding("r", "refresh", "Refresh Sources", show=True),
        Binding("p", "switch_project", "Switch Project", show=True),
        Binding("s", "share", "Share to Slack", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_project = "default"
        self._init_orchestrator(self.current_project)
        
        self.last_result = None
        # Wizard state
        self.wizard_step = 0
        self.wizard_data = {}
        self.wizard_mode = "add" # "add" or "edit"
        self.target_conn_id = None
        self.conn_map = {} # Map index to conn_id

from backend.utils.slack_notifier import SlackNotifier

class BI_AgentConsole(App):
# ... in __init__ ...
    def _init_orchestrator(self, project_id: str):
        try:
            self.orchestrator = CollaborativeOrchestrator(project_id)
            self.conn_mgr = self.orchestrator.conn_mgr
            self.registry_path = self.conn_mgr.registry_path
            
            # Load project settings (Slack, etc.)
            self.settings_path = os.path.join("projects", project_id, "settings.json")
            self.settings = {"slack_webhook": ""}
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    self.settings.update(json.load(f))
            
            self.notifier = SlackNotifier(self.settings.get("slack_webhook", ""))
            logger.info(f"Orchestrator for project '{project_id}' initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")

    def compose(self) -> ComposeResult:
        yield Label(f"Project: {self.current_project}", id="project-header")
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
        
        try:
            # Check Authentication
            if not auth_manager.is_authenticated():
                self.push_screen(AuthScreen())

            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write("안녕하세요! [bold blue]BI-Agent Console[/bold blue]입니다.")
            
            # Check if we have only sample data
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                if len(registry) == 1 and "sample_sales" in registry:
                    chat_log.write("\n[bold yellow]💡 Tip:[/bold yellow] 현재 연결된 DB가 없어 [bold]샘플 데이터[/bold]를 자동으로 준비했습니다.")
                    chat_log.write("바로 질문을 던져 분석을 체험해 보세요!\n")
            
            chat_log.write("사이드바에서 소스를 선택하고 [bold]E[/bold]나 [bold]Del[/bold]을 눌러 관리해 보세요.\n")
            self.action_refresh()
            logger.info("TUI mounted successfully.")
        except Exception as e:
            logger.error(f"Error during TUI mount: {e}")

    def action_refresh(self) -> None:
        """Reloads the connection list from the registry."""
        try:
            source_list = self.query_one("#source-list", ListView)
            source_list.clear()
            self.conn_map = {}
            
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                for idx, (conn_id, info) in enumerate(registry.items()):
                    icon = "🌐" if info.get("category") == "Cloud" else "📂"
                    source_list.append(ListItem(Label(f"{icon} {info['name']} ({conn_id})")))
                    self.conn_map[idx] = conn_id
                logger.info(f"Refreshed {len(registry)} sources.")
            else:
                source_list.append(ListItem(Label("[dim]No sources registered[/dim]")))
        except Exception as e:
            logger.error(f"Failed to refresh source list: {e}")

    def get_selected_conn_id(self) -> str:
        try:
            source_list = self.query_one("#source-list", ListView)
            if source_list.index is not None and source_list.index in self.conn_map:
                return self.conn_map[source_list.index]
        except Exception as e:
            logger.error(f"Error getting selected connection: {e}")
        return None

    def action_add_connection(self) -> None:
        """Starts the connection wizard in ADD mode."""
        try:
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
                Option("MySQL", id="mysql"),
                Option("DuckDB (Local File/Memory)", id="duckdb")
            ])
            opt_list.add_class("visible")
            opt_list.focus()
        except Exception as e:
            logger.error(f"Error starting Add Connection wizard: {e}")

    def action_edit_connection(self) -> None:
        """Starts the connection wizard in EDIT mode."""
        try:
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
            opt_list.add_options([Option("SQLite", id="sqlite"), Option("Excel", id="excel"), Option("PostgreSQL", id="postgres"), Option("MySQL", id="mysql"), Option("DuckDB", id="duckdb")])
            opt_list.add_class("visible")
            opt_list.focus()
        except Exception as e:
            logger.error(f"Error starting Edit Connection wizard: {e}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handles type selection via arrow keys + Enter."""
        try:
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
        except Exception as e:
            logger.error(f"Error in OptionList selection: {e}")

    def action_delete_connection(self) -> None:
        """Triggers deletion confirmation."""
        try:
            conn_id = self.get_selected_conn_id()
            if not conn_id:
                return
            
            self.wizard_mode = "delete"
            self.target_conn_id = conn_id
            self.wizard_step = 99 # Special step for delete confirmation
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(Panel(f"[bold red]⚠ DELETE CONFIRMATION: {conn_id}[/bold red]", border_style="red"))
            chat_log.write(f"정말로 [bold]'{conn_id}'[/bold] 연결을 삭제하시겠습니까? (삭제하려면 'yes' 입력)")
        except Exception as e:
            logger.error(f"Error starting delete confirmation: {e}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_query = event.value.strip()
        if not user_query:
            return

        try:
            input_widget = self.query_one("#user-input", Input)
            chat_log = self.query_one("#chat-log", RichLog)

            # Clear standard analysis queries immediately
            if self.wizard_step == 0:
                input_widget.value = ""
            
            if self.wizard_step > 0:
                await self.handle_wizard_step(user_query)
            elif user_query.startswith("slack:"):
                # Configure Slack Webhook
                webhook = user_query.replace("slack:", "").strip()
                self.settings["slack_webhook"] = webhook
                with open(self.settings_path, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=2)
                self.notifier = SlackNotifier(webhook)
                chat_log.write(f"\n[bold green]✅ Slack Webhook이 설정되었습니다![/bold green]")
                input_widget.value = ""
            else:
                await self.process_analysis_query(user_query)
            
            if self.wizard_step == 0:
                input_widget.value = ""
            elif self.wizard_step == 2:
                input_widget.value = ""
        except Exception as e:
            logger.error(f"Error handled input submission: {e}")
            self.query_one("#chat-log", RichLog).write(f"[bold red]❌ 입력 처리 중 오류 발생:[/bold red] {str(e)}")

    async def handle_wizard_step(self, value: str) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        input_widget = self.query_one("#user-input", Input)

        try:
            # Deletion Confirmation
            if self.wizard_step == 99:
                if value.lower() == "yes":
                    with open(self.registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                    if self.target_conn_id in registry:
                        del registry[self.target_conn_id]
                        with open(self.registry_path, 'w', encoding='utf-8') as f:
                            json.dump(registry, f, indent=2)
                        chat_log.write(f"\n[bold green]🗑 연결 '{self.target_conn_id}'이(가) 삭제되었습니다.[/bold green]")
                        self.action_refresh()
                else:
                    chat_log.write("\n[yellow]삭제가 취소되었습니다.[/yellow]")
                self.wizard_step = 0
                return

            # Step 2: Name Input
            if self.wizard_step == 2:
                self.wizard_data["name"] = value
                self.wizard_step = 3
                chat_log.write(f" [green]▶ Name:[/green] {value}")
                chat_log.write("[bold cyan]Step 3: 설정 정보 입력[/bold cyan]")
                
                templates = {
                    "sqlite": "backend/data/sample_sales.sqlite",
                    "excel": "path/to/data.xlsx",
                    "postgres": "host=localhost port=5432 dbname=postgres user=postgres password=secret",
                    "mysql": "host=localhost port=3306 dbname=mysql user=root password=secret",
                    "duckdb": "backend/data/local.duckdb"
                }
                template = templates.get(self.wizard_data["type"], "")
                chat_log.write(f" [dim]Template: {template}[/dim]")
                chat_log.write(" [italic blue]* 아래 입력창의 템플릿을 수정하여 입력하세요.[/italic blue]")
                
                input_widget.value = template
                input_widget.focus()

            # Step 3: Config Input & Finalization
            elif self.wizard_step == 3:
                config_input = value
                # Fix Config logic
                if self.wizard_data["type"] in ["sqlite", "excel", "duckdb"]:
                    self.wizard_data["config"] = {"path": config_input}
                else:
                    # Very basic parser for key=value strings
                    try:
                        self.wizard_data["config"] = dict(item.split("=") for item in config_input.split())
                    except:
                        self.wizard_data["config"] = config_input

                # Finalize
                conn_id = self.target_conn_id if self.wizard_mode == "edit" else f"conn_{int(datetime.datetime.now().timestamp())}"
                self.conn_mgr.register_connection(
                    conn_id=conn_id,
                    conn_type=self.wizard_data["type"],
                    config=self.wizard_data["config"],
                    name=self.wizard_data["name"]
                )
                msg = "수정" if self.wizard_mode == "edit" else "등록"
                chat_log.write(Panel(f"[bold green]✨ SUCCESS: 데이터 소스가 성공적으로 {msg}되었습니다![/bold green]", border_style="green"))
                self.action_refresh()
                self.wizard_step = 0
                self.wizard_mode = "add"
                input_widget.placeholder = "대화 분석 시작... 또는 사이드바 관리"

        except Exception as e:
            logger.error(f"Wizard handles error at step {self.wizard_step}: {e}")
            chat_log.write(f"\n[bold red]❌ 작업 실패:[/bold red] {str(e)}")
            self.wizard_step = 0 # Reset on failure

    async def process_analysis_query(self, user_query: str) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        preview = self.query_one("#preview-content", Static)

        chat_log.write(f"[bold green]YOU:[/bold green] {user_query}")
        
        try:
            # Check Registry
            if not os.path.exists(self.registry_path):
                 chat_log.write("[bold red]ERROR:[/bold red] 등록된 데이터 소스가 없습니다.")
                 return
                 
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            # Use selected source if available
            selected_conn = self.get_selected_conn_id()
            conn_id = selected_conn if selected_conn else list(registry.keys())[0]
            
            chat_log.write(f"[bold blue]SYSTEM:[/bold blue] [cyan]'{registry[conn_id]['name']}'[/cyan] 소스에서 분석을 시작합니다...")
            logger.info(f"Processing query '{user_query}' on connection '{conn_id}'")
            
            # handle_complex_request is now async
            result = await self.orchestrator.handle_complex_request(user_query, conn_id)
            self.last_result = result
            
            if result.get("is_simulation"):
                 chat_log.write("[bold yellow]⚠️ SIMULATION MODE:[/bold yellow] 연결이 불안정하여 가상 데이터 스키마를 기반으로 분석을 수행했습니다.")

            chat_log.write(f"[bold blue]BI-Agent:[/bold blue] 분석 결과:")
            chat_log.write(f" > [dim]{result['reasoning']}[/dim]\n")
            
            with open(result["path"], "r", encoding='utf-8') as f:
                meta_json = json.load(f)
            
            syntax = Syntax(json.dumps(meta_json, indent=2), "json", theme="monokai", line_numbers=True)
            title = f"[bold yellow]Preview: {result['summary']['table']}[/bold yellow]"
            if result.get("is_simulation"):
                title += " [bold red](MOCK)[/bold red]"
            preview.update(Panel(syntax, title=title, border_style="yellow"))
            logger.info(f"Query processed successfully. Result saved at {result['path']}")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            chat_log.write(f"[bold red]ERROR:[/bold red] {str(e)}")

    def action_clear_chat(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def action_share(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        if not self.last_result:
            chat_log.write("[bold red]⚠ 오류:[/bold red] 공유할 분석 결과가 없습니다.")
            return

        if not self.settings.get("slack_webhook"):
            chat_log.write("\n[bold yellow]🔌 Slack 설정이 필요합니다.[/bold yellow]")
            chat_log.write("Slack Webhook URL을 입력해 주세요 (형식: [cyan]slack: https://...[/cyan])")
            input_widget = self.query_one("#user-input", Input)
            input_widget.focus()
            input_widget.value = "slack: "
            return

        success = self.notifier.send_report_summary(self.last_result, self.current_project)
        if success:
            chat_log.write(f"\n[bold green]🚀 Slack으로 리포트 요약이 전송되었습니다! ({self.current_project})[/bold green]")
        else:
            chat_log.write("\n[bold red]❌ Slack 전송 실패.[/bold red] Webhook 설정을 확인하세요.")

    def action_save(self) -> None:
        if self.last_result:
            self.query_one("#chat-log", RichLog).write(f"\n[bold cyan]SYSTEM:[/bold cyan] JSON이 {self.last_result['path']}에 보존되었습니다.")

    def action_switch_project(self) -> None:
        def set_project(project_id: str) -> None:
            if project_id:
                self.current_project = project_id
                self._init_orchestrator(project_id)
                self.query_one("#project-header", Label).update(f"Project: {self.current_project}")
                self.action_refresh()
                self.query_one("#chat-log", RichLog).write(f"\n[bold green]🚀 프로젝트 '{project_id}'로 전환되었습니다.[/bold green]")
        
        self.push_screen(ProjectScreen(self.current_project), set_project)

    async def action_quit(self) -> None:
        """Gracefully shutdown and quit."""
        try:
            logger.info("Closing all connection sessions before quit.")
            self.conn_mgr.close_all()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        self.exit()

def run_app():
    try:
        app = BI_AgentConsole()
        app.run()
    except Exception as e:
        logger.critical(f"App crashed on startup: {e}")
        print(f"CRITICAL ERROR: {e}\nCheck logs/tui.log for details.")

if __name__ == "__main__":
    run_app()
