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
