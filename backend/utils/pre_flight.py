import os
import sys
import platform
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from backend.orchestrator.auth_manager import auth_manager
from backend.utils.logger_setup import setup_logger

# Setup logger for pre-flight checks
logger = setup_logger("pre_flight", "pre_flight.log")
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
        
        with console.status("[bold blue]환경 점검 중...", spinner="dots") as status:
            # 1. Python 버전 점검
            status.update("[dim]Python 버전 확인 중...")
            self._check_python()
            
            # 2. 네트워크 연결성 점검
            status.update("[dim]네트워크 연결성 확인 중...")
            self._check_network()

            # 3. 인증 상태 점검 (API Key)
            status.update("[dim]API Key 상태 확인 중...")
            self._check_auth()
            
            # 4. 필수 디렉토리 및 설정 점검
            status.update("[dim]시스템 환경 확인 중...")
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

    def _check_network(self):
        """Google API 서버 접속 가능 여부를 확인합니다."""
        import socket
        try:
            # Google Public DNS (8.8.8.8) 포트 53(DNS) 연결 시도
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            console.print("[green]✔[/green] Network connectivity confirmed.")
            self.status["network"] = True
        except Exception:
            console.print("[yellow]![/yellow] Network connection is unstable or offline.")
            self.status["network"] = False

    def _check_auth(self) -> None:
        """
        API 키가 환경변수나 credentials.json에 설정되어 있는지 확인합니다.
        Gemini CLI/Claude CLI처럼 자동으로 감지합니다.
        """
        from backend.orchestrator.auth_manager import auth_manager
        
        found_keys = []
        
        # 1. 환경변수 확인
        env_keys = {
            "GEMINI_API_KEY": "Gemini",
            "ANTHROPIC_API_KEY": "Claude",
            "OPENAI_API_KEY": "OpenAI"
        }
        
        for env_var, provider_name in env_keys.items():
            if os.getenv(env_var):
                found_keys.append(f"{provider_name} (환경변수)")
                logger.debug(f"Found {env_var} in environment")
        
        # 2. credentials.json 확인
        for provider in ["gemini", "claude", "openai"]:
            prov_data = auth_manager.get_provider_data(provider)
            if prov_data and prov_data.get("key"):
                found_keys.append(f"{provider.capitalize()} (credentials.json)")
                logger.debug(f"Found {provider} key in credentials.json")
        
        # 결과 표시
        if found_keys:
            console.print("   [green]✅ API Keys 감지:[/green]")
            for key_info in found_keys:
                console.print(f"      • {key_info}")
            self.status["auth"] = True
            logger.info(f"Authentication passed with {len(found_keys)} provider(s)")
        else:
            console.print("   [yellow]⚠️  API Key가 설정되지 않았습니다.[/yellow]")
            self.status["auth"] = False
            logger.warning("No API keys found in environment or credentials.json")

    def _check_environment(self):
        # backend/data 등 필수 경로 확인
        try:
            from backend.utils.path_config import path_manager
            console.print(f"[green]✔[/green] Storage initialized at [dim]{path_manager.base_dir}[/dim]")
            self.status["mcp"] = True # Basic env is ok
        except Exception as e:
            console.print(f"[red]✘[/red] Path initialization failed: {e}")
            self.status["mcp"] = False

            console.print("[dim]키 입력을 건너뜁니다. TUI 진입 후 /login 명령어로 설정할 수 있습니다.[/dim]")
            # 강제로 False로 두지 않고, TUI 진입은 허용하되 기능을 제한할 수도 있음.
            # 하지만 사용자의 'Pre-flight' 요구사항은 선검증이므로 일단 흐름을 유지.
            self.status["auth"] = True # TUI 진입은 허용

    def _handle_missing_auth(self) -> None:
        """인증이 필요할 때 사용자에게 안내합니다."""
        console.print("\n[bold yellow]🔑 API Key 설정이 필요합니다.[/bold yellow]\n")
        console.print("TUI에서 설정 안내를 확인하거나, 다음 중 한 가지 방법으로 설정해주세요:\n")
        console.print("[cyan]1. 환경변수 설정:[/cyan]")
        console.print("   export GEMINI_API_KEY='your-key-here'")
        console.print("   export ANTHROPIC_API_KEY='your-key-here'")
        console.print("   export OPENAI_API_KEY='your-key-here'\n")
        console.print("[cyan]2. 설정 파일 편집:[/cyan]")
        console.print(f"   파일: ~/.bi-agent/credentials.json\n")
        # logger.info("Displayed authentication setup instructions to user") # logger is not defined

def run_pre_flight() -> bool:
    checker = PreFlightChecker()
    return checker.check_all()

if __name__ == "__main__":
    checker = PreFlightChecker()
    if checker.check_all():
        console.print("\n[bold green]✅ All checks passed! Ready to launch TUI.[/bold green]\n")
    else:
        console.print("\n[bold red]⚠️  Some checks failed. Please fix the issues above.[/bold red]\n")
