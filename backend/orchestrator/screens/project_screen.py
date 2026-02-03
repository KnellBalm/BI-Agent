from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Input, ListView, ListItem
from textual.screen import ModalScreen

from backend.utils.path_config import path_manager

class ProjectScreen(ModalScreen):
    """
    Project selection and creation screen.
    """
    def __init__(self, current_project: str):
        super().__init__()
        self.current_project = current_project
        self.proj_map = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="project-modal"):
            yield Label("[bold indigo]🗂️ 프로젝트 관리자[/bold indigo]", id="project-title")
            yield Label(f"현재 선택: [indigo]{self.current_project}[/indigo]\n")
            yield Label("프로젝트를 선택하거나 새로 생성하세요:")
            yield ListView(id="project-list")
            yield Input(id="new-project-input", placeholder="새 프로젝트 이름을 입력하세요...")
            yield Label("\n[dim]Esc:취소  Enter:선택/생성[/dim]")

    CSS = """
    #project-modal {
        width: 60;
        height: 24;
        background: #000000;
        border: thick #4f46e5;
        padding: 2;
        align: center middle;
    }
    #project-title {
        text-align: center;
        margin-bottom: 1;
    }
    #project-list {
        height: 10;
        background: #050505;
        border: solid #111111;
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
