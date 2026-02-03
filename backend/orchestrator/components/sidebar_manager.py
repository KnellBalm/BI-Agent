import os
import json
import logging
from typing import Iterable, Any, Dict, List, Optional, Union
from textual.app import App, ComposeResult
from textual.widgets import Label, Static
from rich.markup import escape

from backend.orchestrator.managers.auth_manager import auth_manager
from backend.orchestrator.managers.quota_manager import quota_manager
from backend.orchestrator.managers.context_manager import context_manager

logger = logging.getLogger("tui")

class SidebarManager:
    """
    사이드바 상태 업데이트 로직을 담당하는 매니저
    """
    def __init__(self, app: App):
        self.app = app
        # registry_path는 App 인스턴스에서 직접 참조하도록 유도하거나 명시적으로 전달받음
        self.registry_path = getattr(app, "registry_path", None)

    def compose(self) -> ComposeResult:
        """사이드바 위젯 구성 (컴포넌트 위임용)"""
        yield Label("[bold]PROJECT[/bold]", classes="sidebar-title")
        yield Label("• [dim]default[/dim]", id="lbl-project")
        
        yield Label("\n[bold]STATUS[/bold]", classes="sidebar-title")
        yield Label("• Auth: [red]✘[/red]", id="lbl-auth")
        yield Label("• Context: [red]✘[/red]", id="lbl-context")
        
        yield Label("\n[bold]QUOTA USAGE[/bold]", classes="sidebar-title")
        yield Static("Loading...", id="lbl-quota")
        
        yield Label("\n[bold]CONNECTIONS[/bold]", classes="sidebar-title")
        yield Static("[dim]No sources.[/dim]", id="lbl-connections")
        
        yield Label("\n[bold]JOURNEY PROGRESS[/bold]", classes="sidebar-title")
        yield Static("Launch -> Auth -> Conn", id="lbl-journey")
        
        yield Label("\n[bold]ACTION RECOMMENDATION[/bold]", classes="sidebar-title")
        yield Static("초기 설정을 진행하세요.", id="lbl-recommend")

    async def update(self) -> None:
        """Update the sidebar status information."""
        try:
            # Project status
            project_lbl = self.app.query_one("#lbl-project", Label)
            current_project = os.environ.get("AG_PROJECT_ID", "default")
            project_lbl.update(f"• [indigo]{current_project}[/indigo]")

            # Auth status
            auth_lbl = self.app.query_one("#lbl-auth", Label)
            active_providers = []
            for p in ["gemini", "claude", "openai"]:
                if auth_manager.is_authenticated(p):
                    active_providers.append(p.capitalize())
            
            if active_providers:
                auth_lbl.update(f"• Auth: [green]✔ {', '.join(active_providers)}[/green]")
            else:
                auth_lbl.update("• Auth: [red]✘ Login Required[/red]")

            # Quota status
            quota_lbl = self.app.query_one("#lbl-quota", Static)
            quota_text = ""
            for p in ["gemini", "claude", "openai", "ollama"]:
                status = quota_manager.get_provider_status(p)
                usage = status.get('daily_count', 0)
                limit = status.get('limit', 1500)
                
                if limit != "∞" and isinstance(limit, int):
                    percent = min(100, int((usage / limit) * 100))
                    bar_len = 10
                    filled = int(percent / 100 * bar_len)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    
                    if percent < 50: color = "green"
                    elif percent < 80: color = "yellow"
                    else: color = "red"
                    
                    emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                    quota_text += f"{emoji} [{color}]{bar}[/{color}] {usage}/{limit}\n"
                else:
                    emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                    quota_text += f"{emoji} {p.capitalize()}: {usage}/∞\n"
            
            quota_lbl.update(quota_text.strip())

            # Analysis Context
            context_lbl = self.app.query_one("#lbl-context", Label)
            context_summary = context_manager.get_context_summary()
            if context_manager.active_table:
                context_lbl.update(f"• [indigo]{context_summary}[/indigo]")
            else:
                context_lbl.update("• [dim]No active context[/dim]")

            # Journey Progress
            journey_lbl = self.app.query_one("#lbl-journey", Static)
            steps = ["Launch", "Auth", "Conn", "Expl", "Pin", "Anlyz", "Rslt"]
            current_step = context_manager.journey_step
            
            journey_bar = ""
            for i, step_name in enumerate(steps):
                if i < current_step:
                    color = "green"
                    symbol = "✔"
                elif i == current_step:
                    color = "indigo"
                    symbol = "→"
                else:
                    color = "dim"
                    symbol = "○"
                journey_bar += f"[{color}]{symbol} {step_name}[/{color}]\n"
            journey_lbl.update(journey_bar.strip())

            # Connection status
            conn_lbl = self.app.query_one("#lbl-connections", Static)
            if self.registry_path and os.path.exists(self.registry_path):
                try:
                    with open(self.registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                    if registry:
                        conn_lines = []
                        for name, info in registry.items():
                            c_type = info.get('type', 'unknown')
                            conn_lines.append(f"• {escape(str(name))} [dim]({escape(str(c_type))})[/dim]")
                        conn_lbl.update("\n".join(conn_lines))
                    else:
                        conn_lbl.update("[dim]No sources connected.[/dim]")
                except Exception as e:
                    logger.error(f"Error loading registry from {self.registry_path}: {e}")
                    conn_lbl.update("[red]Error loading registry[/red]")
            else:
                conn_lbl.update("[dim]No sources connected.[/dim]")

            # Action Recommendation
            recommend_lbl = self.app.query_one("#lbl-recommend", Static)
            recommendations = {
                0: "AI 설정을 위해 [b][indigo]/login[/indigo][/b]을 먼저 수행해 주세요.",
                1: "이제 데이터를 연결할 차례입니다. [b][indigo]/connect[/indigo][/b]를 입력하세요.",
                2: "데이터가 연결되었습니다! [b][indigo]/explore [conn_id][/indigo][/b]로 테이블을 확인하세요.",
                3: "테이블을 탐색 중입니다. 분석할 테이블을 [b][indigo]/explore [table][/indigo][/b]로 선택하세요.",
                4: "테이블이 선택되었습니다. 질문을 입력하거나 [b][indigo]/analyze[/indigo][/b]를 실행해 보세요!",
                5: "분석이 진행 중입니다. 결과를 기다려 주세요.",
                6: "분석 완료! 시각화 결과('v' 키)를 확인하거나 추가 질문을 던져보세요."
            }
            tip = recommendations.get(current_step, recommendations[len(recommendations)-1])
            recommend_lbl.update(tip)

        except Exception as e:
            logger.error(f"Sidebar update failed: {e}")
