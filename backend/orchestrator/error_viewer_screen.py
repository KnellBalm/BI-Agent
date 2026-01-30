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
        error_log_path = project_root / "logs" / "textual_errors.log"
        
        content_widget = self.query_one("#error-content", Static)
        
        if not error_log_path.exists():
            content_widget.update("[dim green]✨ No errors recorded yet! Everything is working smoothly.[/dim]")
            return
        
        try:
            with open(error_log_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 최근 부분만 표시 (너무 길면)
            if len(content) > 10000:
                content = "... (showing last 10000 characters)\\n" + content[-10000:]
            
            if content.strip():
                content_widget.update(content)
            else:
                content_widget.update("[dim green]✨ No errors recorded yet! Everything is working smoothly.[/dim]")
        except Exception as e:
            content_widget.update(f"[red]Failed to read error log: {e}[/red]")
    
    def action_dismiss(self) -> None:
        self.dismiss()
