# ErrorViewerScreen 별도 파일로 생성 (임시)

from textual.screen import ModalScreen
from textual.widgets import Label, Static
from textual.containers import Container
from textual.app import ComposeResult


class ErrorViewerScreen(ModalScreen):
    """최근 발생한 Textual 에러를 확인할 수 있는 화면"""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]
    
    CSS = """
    ErrorViewerScreen {
        align: center middle;
    }
    #error-modal {
        width: 90;
        height: 30;
        background: #1e293b;
        border: thick #ef4444;
        padding: 1;
    }
    #error-title {
        text-align: center;
        color: #ef4444;
        text-style: bold;
        margin-bottom: 1;
    }
    #error-content {
        height: 1fr;
        background: #0f172a;
        border: solid #6366f1;
        padding: 1;
        overflow-y: scroll;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="error-modal"):
            yield Label("🔍 Recent System Errors (logs/textual_errors.log)", id="error-title")
            yield Static(id="error-content")
            yield Label("\\n[dim]Press ESC to close | Select text to copy[/dim]", classes="guide-text")
    
    def on_mount(self) -> None:
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent
        # tui.log도 함께 확인
        tui_log_path = project_root / "logs" / "tui.log"
        error_log_path = project_root / "logs" / "textual_errors.log"
        content_text = ""
        
        content_widget = self.query_one("#error-content", Static)

        # Read tui.log
        if tui_log_path.exists():
            try:
                with open(tui_log_path, "r", encoding="utf-8") as f:
                    tui_content = f.read()
                    if tui_content.strip():
                        content_text += "[bold cyan]--- TUI Logic Log (logs/tui.log) ---[/bold cyan]\n"
                        # Display last 5000 characters
                        if len(tui_content) > 5000:
                            content_text += "... (showing last 5000 characters)\n"
                        content_text += tui_content[-5000:] + "\n\n"
            except Exception as e:
                content_text += f"[red]Failed to read tui.log: {e}[/red]\n\n"

        # Read textual_errors.log
        if error_log_path.exists():
            try:
                with open(error_log_path, "r", encoding="utf-8") as f:
                    err_content = f.read()
                    if err_content.strip():
                        content_text += "[bold red]--- Textual App Errors (logs/textual_errors.log) ---[/bold red]\n"
                        # Display last 5000 characters
                        if len(err_content) > 5000:
                            content_text += "... (showing last 5000 characters)\n"
                        content_text += err_content[-5000:]
            except Exception as e:
                content_text += f"[red]Failed to read textual_errors.log: {e}[/red]\n\n"

        if content_text.strip():
            content_widget.update(content_text)
        else:
            content_widget.update("[dim green]✨ No logs recorded yet! Everything is working smoothly.[/dim]")
    
    def action_dismiss(self) -> None:
        self.dismiss()
