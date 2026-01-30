"""
메시지 버블 및 대화 관련 컴포넌트
tenere 및 claude streaming 스타일 참조
"""
from datetime import datetime
from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import VerticalScroll
from rich.syntax import Syntax
from rich.markdown import Markdown


class MessageBubble(Static):
    """
    대화 메시지 버블 컴포넌트
    
    역할별로 다른 스타일 적용:
    - user: 사용자 메시지
    - agent: AI 에이전트 응답
    - system: 시스템 메시지
    - thinking: 에이전트 사고 과정
    """
    
    DEFAULT_CSS = """
    MessageBubble {
        width: 100%;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    
    .msg-user {
        background: #111214;
        border-right: thick #3b82f6;
        text-align: right;
    }
    
    .msg-agent {
        background: #1a1b1e;
        border-left: thick #10b981;
    }
    
    .msg-system {
        background: #1a1b1e;
        border-left: thick #f59e0b;
        color: #f59e0b;
    }
    
    .msg-thinking {
        background: #161b22;
        border-left: thick #7c3aed;
        color: #a78bfa;
        text-style: italic;
    }
    
    .msg-header {
        text-style: bold;
        margin-bottom: 0;
    }
    
    .msg-timestamp {
        color: #4b5563;
        text-style: dim;
    }
    
    .msg-content {
        color: #e2e8f0;
    }
    """
    
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.add_class(f"msg-{role}")
    
    def render(self) -> str:
        """메시지 렌더링"""
        # 역할별 아이콘 및 컬러
        icons = {
            "user": "👤",
            "agent": "🤖",
            "system": "⚙️",
            "thinking": "💭"
        }
        colors = {
            "user": "#60a5fa",
            "agent": "#34d399",
            "system": "#fbbf24",
            "thinking": "#a78bfa"
        }
        
        icon = icons.get(self.role, "💬")
        color = colors.get(self.role, "#cbd5e1")
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        # 헤더
        header = f"[{color}]{icon} {self.role.title()}[/{color}] [dim]{time_str}[/dim]"
        
        # 컨텐츠
        content = self._format_content()
        
        return f"{header}\n{content}"
    
    def _format_content(self) -> str:
        """컨텐츠 포맷팅 (마크다운, 코드 블록 등)"""
        # 간단한 마크다운 지원
        # 추후 Rich의 Markdown 클래스 사용 가능
        return self.content


class ThinkingPanel(Static):
    """
    에이전트의 사고 과정을 표시하는 패널
    
    실시간으로 업데이트되며, 현재 추론 중인 내용을 표시
    """
    
    DEFAULT_CSS = """
    ThinkingPanel {
        width: 100%;
        height: auto;
        background: #161b22;
        border: solid #7c3aed;
        padding: 1 2;
        margin: 1 0;
    }
    
    .thinking-header {
        color: #7c3aed;
        text-style: bold italic;
        margin-bottom: 1;
    }
    
    .thinking-content {
        color: #cbd5e1;
    }
    
    .thinking-step {
        margin-left: 2;
        color: #94a3b8;
    }
    """
    
    thinking_content = reactive("")
    steps = reactive([])
    
    def render(self) -> str:
        """패널 렌더링"""
        if not self.thinking_content and not self.steps:
            return "[dim italic]에이전트가 사고 중입니다...[/dim italic]"
        
        lines = ["[bold]💭 Agent Thinking[/bold]"]
        
        if self.thinking_content:
            lines.append(f"\n{self.thinking_content}")
        
        if self.steps:
            lines.append("\n[bold]Steps:[/bold]")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"  {i}. {step}")
        
        return "\n".join(lines)
    
    def update_thinking(self, content: str):
        """사고 내용 업데이트"""
        self.thinking_content = content
    
    def add_step(self, step: str):
        """추론 단계 추가"""
        new_steps = list(self.steps)
        new_steps.append(step)
        self.steps = new_steps[-5:]  # 최근 5개만 유지
    
    def clear(self):
        """내용 초기화"""
        self.thinking_content = ""
        self.steps = []


class StreamingMessageView(Static):
    """
    스트리밍 메시지 뷰 - 실시간으로 토큰이 추가됨
    """
    
    DEFAULT_CSS = """
    StreamingMessageView {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: #1a1b1e;
        border-left: thick #10b981;
    }
    
    .streaming-header {
        color: #10b981;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .streaming-content {
        color: #e2e8f0;
    }
    
    .streaming-cursor {
        background: #10b981;
        color: #0c0c0e;
    }
    """
    
    content = reactive("")
    is_streaming = reactive(True)
    
    def render(self) -> str:
        """스트리밍 컨텐츠 렌더링"""
        header = "[bold]🤖 Agent[/bold]"
        
        # 스트리밍 중일 때 커서 표시
        cursor = "▊" if self.is_streaming else ""
        
        return f"{header}\n{self.content}[reverse]{cursor}[/reverse]"
    
    def append_token(self, token: str):
        """토큰 추가"""
        self.content += token
    
    def complete(self):
        """스트리밍 완료"""
        self.is_streaming = False


class ToolActivityTracker(Static):
    """
    실행 중인 도구를 실시간으로 표시
    """
    
    DEFAULT_CSS = """
    ToolActivityTracker {
        width: 100%;
        height: auto;
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1 0;
    }
    
    .tool-header {
        color: #94a3b8;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .tool-running {
        color: #f59e0b;
    }
    
    .tool-complete {
        color: #10b981;
    }
    """
    
    active_tools = reactive([])
    
    def render(self) -> str:
        """도구 활동 렌더링"""
        if not self.active_tools:
            return "[dim]도구 활동 없음[/dim]"
        
        lines = ["[bold]🔧 Tool Activity[/bold]\n"]
        
        for tool in self.active_tools:
            status = tool.get('status', 'running')
            name = tool.get('name', 'Unknown')
            target = tool.get('target', '')
            duration = tool.get('duration', 0)
            
            if status == 'running':
                icon = "⏳"
                color = "yellow"
                line = f"[{color}]{icon} {name}[/{color}]"
                if target:
                    line += f" - {target}"
            else:  # complete
                icon = "✓"
                color = "green"
                line = f"[{color}]{icon} {name}[/{color}]"
                if duration:
                    line += f" ({duration}s)"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def add_tool(self, name: str, target: str = "", status: str = 'running'):
        """도구 추가"""
        new_tools = list(self.active_tools)
        new_tools.append({
            'name': name,
            'target': target,
            'status': status,
            'start_time': datetime.now()
        })
        self.active_tools = new_tools
    
    def complete_tool(self, name: str):
        """도구 완료 처리"""
        new_tools = []
        for tool in self.active_tools:
            if tool['name'] == name and tool['status'] == 'running':
                duration = (datetime.now() - tool['start_time']).total_seconds()
                tool['status'] = 'complete'
                tool['duration'] = int(duration)
            new_tools.append(tool)
        self.active_tools = new_tools
    
    def clear_completed(self):
        """완료된 도구 제거"""
        self.active_tools = [t for t in self.active_tools if t['status'] == 'running']
