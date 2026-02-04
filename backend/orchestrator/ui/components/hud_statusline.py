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
    
    표시 정보:
    - 현재 사용 중인 LLM 모델
    - 컨텍스트 사용률 (시각적 프로그레스 바)
    - 프로젝트 정보
    - 도구 활동
    - 에이전트 상태
    - 세션 시간
    """
    
    DEFAULT_CSS = """
    HUDStatusLine {
        height: 3;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 2;
        color: #f8fafc;
    }
    
    .hud-line {
        height: 1;
    }
    """
    
    # Reactive properties
    current_model = reactive("Gemini 2.0 Flash")
    context_usage = reactive(0.0)  # 0-100
    project_name = reactive("default")
    active_tools = reactive([])
    active_agents = reactive([])
    session_start = reactive(datetime.now())
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_start = datetime.now()
    
    def render(self) -> str:
        """HUD를 렌더링"""
        lines = []
        
        # 첫 번째 라인: 세션 정보
        lines.append(self._render_session_info())
        
        # 두 번째 라인: 도구 활동
        lines.append(self._render_tool_activity())
        
        # 세 번째 라인: 에이전트 상태 (있을 경우)
        if self.active_agents:
            lines.append(self._render_agent_status())
        
        return "\n".join(lines)
    
    def _render_session_info(self) -> str:
        """세션 정보 라인 렌더링"""
        # 컨텍스트 바 생성
        bar_length = 10
        filled = int(self.context_usage / 10)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # 컬러 코딩
        if self.context_usage < 50:
            color = "green"
        elif self.context_usage < 80:
            color = "yellow"
        else:
            color = "red"
        
        # 세션 시간 계산
        duration = datetime.now() - self.session_start
        duration_str = self._format_duration(duration.total_seconds())
        
        # 모델명 단축
        model_short = self._shorten_model_name(self.current_model)
        
        return (
            f"[bold cyan]{model_short}[/bold cyan] | "
            f"[{color}]{bar} {self.context_usage:.0f}%[/{color}] | "
            f"📂 [cyan]{self.project_name}[/cyan] | "
            f"⏱️ {duration_str}"
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
