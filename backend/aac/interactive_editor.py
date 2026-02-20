"""
AaC Interactive Editor — Textual 기반 마크다운 내장 에디터
"""
import os
from textual.app import App, ComposeResult
from textual.widgets import TextArea, Header, Footer
from textual.binding import Binding
from textual.containers import Vertical

class MarkdownEditorApp(App):
    """지정된 마크다운 파일을 편집하는 전체 화면 Textual 에디터 모달."""
    
    CSS = """
    Screen {
        background: $surface-darken-1;
    }
    TextArea {
        height: 1fr;
        width: 100%;
        border: none;
        background: $surface;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+s", "save", "저장 후 닫기"),
        Binding("escape", "cancel", "닫기 (저장 안 함)"),
    ]

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.content = ""
        self.title = f"BI-Agent Markdown Editor: {file_path}"
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                self.content = f.read()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            text_area = TextArea(self.content, language="markdown")
            # Textual의 TextArea는 내부적으로 syntax highlighting을 지원 (tree-sitter 연동 시)
            yield text_area
        yield Footer()

    def on_mount(self) -> None:
        """포커스를 에디터에 자동 지정"""
        text_area = self.query_one(TextArea)
        text_area.focus()

    def action_save(self) -> None:
        """내용을 파일에 쓰고 앱 종료"""
        text_area = self.query_one(TextArea)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(text_area.text)
        self.exit(result=True)

    def action_cancel(self) -> None:
        """저장하지 않고 앱 종료"""
        self.exit(result=False)
