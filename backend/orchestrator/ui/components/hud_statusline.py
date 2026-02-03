"""
HUD 스타일의 실시간 상태바 컴포넌트
oh-my-claudecode 및 claude-hud 스타일을 참조하여 구현
"""
from datetime import datetime
from textual.reactive import reactive
from textual.widgets import Static
from typing import List, Dict, Any


class HUDStatusLine(Static):
    """
    Claude HUD 스타일의 실시간 상태바
    """
    
    current_model = reactive("Gemini 2.0 Flash")
    context_usage = reactive(0.0)
    project_name = reactive("default")
    active_tools = reactive([])
    active_agents = reactive([])

    DEFAULT_CSS = """
    HUDStatusLine {
        height: 1;
        background: #050505;
        color: #f8fafc;
        padding: 0 1;
    }
    """
    
    def render(self) -> str:
        """HUD를 1줄로 집약적으로 렌더링"""
        # 컨텍스트 바
        bar_length = 5
        filled = int(self.context_usage / 20)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # 모델 및 프로젝트
        model_short = self._shorten_model_name(self.current_model)
        
        # 도구 상태 요약
        running_tools = [t for t in self.active_tools if t.get('status') == 'running']
        tool_status = f" [yellow]⏳ {running_tools[0]['name']}[/yellow]" if running_tools else ""
        
        return (
            f"[bold #4f46e5]BI-AGENT[/bold #4f46e5] | "
            f"[bold indigo]{model_short}[/bold indigo] | "
            f"CTX {bar} {self.context_usage:.0f}% | "
            f"PRJ [indigo]{self.project_name}[/indigo] | "
            f"{tool_status}"
        )
    
    def _render_tool_activity(self) -> str:
        """도구 활동 라인 렌더링"""
        if not self.active_tools:
            return "[dim]대기 중...[/dim]"
        
        # 완료된 도구들을 카운트별로 그룹화
        tool_counts = {}
        for tool in self.active_tools:
            name = tool.get('name', 'Unknown')
            if tool.get('status') == 'complete':
                tool_counts[name] = tool_counts.get(name, 0) + 1
        
        # 포맷팅
        items = [f"✓ {name} ×{count}" for name, count in tool_counts.items()]
        
        # 현재 실행 중인 도구 표시
        running = [t for t in self.active_tools if t.get('status') == 'running']
        for tool in running[:2]:  # 최대 2개만 표시
            items.insert(0, f"⏳ {tool.get('name', 'Unknown')}")
        
        return " | ".join(items) if items else "[dim]대기 중...[/dim]"
    
    def _render_agent_status(self) -> str:
        """에이전트 상태 라인 렌더링"""
        items = []
        for agent in self.active_agents[:3]:  # 최대 3개
            name = agent.get('name', 'Unknown')
            task = agent.get('task', '')
            duration = agent.get('duration', 0)
            
            status = f"✓ {name}: {task}" if task else f"✓ {name}"
            if duration > 0:
                status += f" ({duration}s)"
            
            items.append(status)
        
        return " | ".join(items) if items else ""
    
    def _shorten_model_name(self, model: str) -> str:
        """모델명 단축"""
        shortcuts = {
            "Gemini 2.0 Flash": "Gemini Flash",
            "Claude 3.5 Sonnet": "Claude Sonnet",
            "GPT-4o": "GPT-4o",
            "Ollama": "Ollama"
        }
        return shortcuts.get(model, model)
    
    def _format_duration(self, seconds: float) -> str:
        """시간 포맷팅"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"
    
    def update_model(self, model: str):
        """현재 모델 업데이트"""
        self.current_model = model
    
    def update_context(self, usage: float):
        """컨텍스트 사용률 업데이트 (0-100)"""
        self.context_usage = min(100, max(0, usage))
    
    def add_tool_activity(self, name: str, status: str = 'running', duration: int = 0):
        """도구 활동 추가"""
        new_tools = list(self.active_tools)
        new_tools.append({
            'name': name,
            'status': status,
            'duration': duration,
            'timestamp': datetime.now()
        })
        # 최근 10개만 유지
        self.active_tools = new_tools[-10:]
    
    def complete_tool(self, name: str, duration: int = 0):
        """도구 완료 처리"""
        self.add_tool_activity(name, 'complete', duration)
    
    def add_agent(self, name: str, task: str = "", duration: int = 0):
        """에이전트 추가"""
        new_agents = list(self.active_agents)
        new_agents.append({
            'name': name,
            'task': task,
            'duration': duration
        })
        self.active_agents = new_agents[-3:]  # 최대 3개
    
    def clear_agents(self):
        """에이전트 목록 초기화"""
        self.active_agents = []
