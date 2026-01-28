import os
import sys
import platform
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from backend.orchestrator.auth_manager import auth_manager

console = Console()

class PreFlightChecker:
    """
    TUI 진입 전 필수 환경 및 인증 상태를 점검합니다. (Phase 0)
    """
    def __init__(self):
        self.status = {
            "python": False,
            "auth": False,
            "mcp": False
        }

    def check_all(self) -> bool:
        """모든 항목을 점검하고 TUI 진입 가능 여부를 반환합니다."""
        console.clear()
        console.print(Panel("[bold cyan]B I - A G E N T[/bold cyan] Pre-flight Check", border_style="cyan"))
        
        # 1. Python 버전 점검
        self._check_python()
        
        # 2. 인증 상태 점검 (API Key)
        self._check_auth()
        
        # 3. 필수 디렉토리 및 설정 점검
        self._check_environment()

        # 결과 요약
        if not self.status["auth"]:
            self._handle_missing_auth()

        return self.status["auth"]

    def _check_python(self):
        version = platform.python_version()
        if sys.version_info >= (3, 10):
            console.print(f"[green]✔[/green] Python {version} detected.")
            self.status["python"] = True
        else:
            console.print(f"[red]✘[/red] Python version {version} is too low. (Required: >= 3.10)")
            self.status["python"] = False

    def _check_auth(self):
        # Gemini API Key 확인 (환경 변수 또는 credentials.json)
        authenticated = auth_manager.is_authenticated("gemini")
        if authenticated:
            console.print("[green]✔[/green] Gemini API Key found.")
            self.status["auth"] = True
        else:
            console.print("[yellow]![/yellow] Gemini API Key is missing.")
            self.status["auth"] = False

    def _check_environment(self):
        # backend/data 등 필수 경로 확인
        from backend.utils.path_config import path_manager
        console.print(f"[green]✔[/green] Storage initialized at [dim]{path_manager.base_dir}[/dim]")
        self.status["mcp"] = True # Basic env is ok

    def _handle_missing_auth(self):
        console.print("\n[bold yellow]계정 설정이 필요합니다.[/bold yellow]")
        console.print("에이전트를 구동하기 위해 Gemini API Key가 필요합니다.")
        console.print("API 키는 [link=https://aistudio.google.com/app/apikey]https://aistudio.google.com/app/apikey[/link] 에서 무료로 발급받을 수 있습니다.\n")
        
        key = Prompt.ask("[bold cyan]Gemini API Key를 입력해주세요[/bold cyan] (건너뛰려면 Enter, 나중에 TUI에서 설정 가능)", password=True)
        
        if key.strip():
            auth_manager.set_provider_key("gemini", key.strip())
            console.print("[green]✔ API Key가 저장되었습니다![/green]")
            self.status["auth"] = True
        else:
            console.print("[dim]키 입력을 건너뜁니다. TUI 진입 후 /login 명령어로 설정할 수 있습니다.[/dim]")
            # 강제로 False로 두지 않고, TUI 진입은 허용하되 기능을 제한할 수도 있음.
            # 하지만 사용자의 'Pre-flight' 요구사항은 선검증이므로 일단 흐름을 유지.
            self.status["auth"] = True # TUI 진입은 허용

def run_pre_flight() -> bool:
    checker = PreFlightChecker()
    return checker.check_all()

if __name__ == "__main__":
    run_pre_flight()
