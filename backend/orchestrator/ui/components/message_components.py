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
    고급스러운 대화 메시지 버블 컴포넌트
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
    
    def on_mount(self) -> None:
        """마운트 시 페이드인 효과 적용"""
        self.styles.opacity = 0.0
        self.styles.animate("opacity", value=1.0, duration=0.3, easing="out_quad")

    def render(self) -> Markdown:
        """메시지 렌더링 (Markdown 지원)"""
        themes = {
            "user": ("●", "medium_purple"),
            "agent": ("◆", "cornflower_blue"),
            "system": ("○", "bright_black"),
        }
        
        icon, color = themes.get(self.role, ("●", "white"))
        time_str = self.timestamp.strftime("%H:%M")
        
        # 헤더 구성 (미니멀 스타일)
        header = f"[{color}][bold]{icon} {self.role.upper()}[/bold] [dim]{time_str}[/dim][/{color}]"
        
        return Markdown(f"{header}\n\n{self.content}")


class ThinkingBubble(Static):
    """
    에이전트가 생각 중임을 나타내는 애니메이션 버블
    """
    
    
    
    dots = reactive(1)
    
    def on_mount(self) -> None:
        """도트 애니메이션 시작"""
        self.set_interval(0.5, self._update_dots)
    
    def _update_dots(self) -> None:
        """도트 개수 순환 업데이트"""
        self.dots = (self.dots % 3) + 1
    
    def render(self) -> str:
        """로딩 메시지 렌더링 (미니멀 CLI 스타일)"""
        return f"[dim]◆ [italic]thinking{'.' * self.dots}[/italic][/dim]"


class ThinkingPanel(Static):
    """
    에이전트의 사고 과정을 표시하는 패널

    실시간으로 업데이트되며, 현재 추론 중인 내용을 표시
    AgentMessageBus를 통해 자동으로 메시지를 수신하여 업데이트
    """

    

    # Reactive attributes for real-time updates
    thinking_content = reactive("")
    steps = reactive([])
    current_step: reactive[str | None] = reactive(None)
    completed_steps: reactive[list[str]] = reactive([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from backend.orchestrator.messaging.agent_message_bus import AgentMessageBus
        self.message_bus = AgentMessageBus()
        self.step_details: dict[str, dict] = {}  # step_id -> {status, description, details, etc.}
        self._pulse_timer = None

    def on_mount(self) -> None:
        """Subscribe to message bus when mounted"""
        self.message_bus.subscribe(self._handle_message)
        logger.debug("ThinkingPanel mounted and subscribed to message bus")

    def on_unmount(self) -> None:
        """Unsubscribe from message bus when unmounted"""
        self.message_bus.unsubscribe(self._handle_message)
        if self._pulse_timer:
            self._pulse_timer.stop()
        logger.debug("ThinkingPanel unmounted and unsubscribed from message bus")

    def _handle_message(self, message) -> None:
        """Handle incoming messages from AgentMessageBus"""
        from backend.orchestrator.messaging.agent_message_bus import MessageType

        try:
            if message.message_type == MessageType.THINKING:
                self._update_current_thinking(message.content)
            elif message.message_type == MessageType.PROGRESS:
                step = message.metadata.get("step")
                total = message.metadata.get("total")
                step_id = message.metadata.get("step_id", f"step_{step}")
                description = message.metadata.get("description", message.content)
                self._update_progress(step, total, step_id, description)
            elif message.message_type == MessageType.COMPLETE:
                step_id = message.metadata.get("step_id")
                if step_id:
                    self._mark_complete(step_id)
            elif message.message_type == MessageType.ERROR:
                self._show_error(message.content)
        except Exception as e:
            logger.error(f"Error handling message in ThinkingPanel: {e}", exc_info=True)

    def _update_current_thinking(self, content: str) -> None:
        """Update the current thinking message with animation"""
        self.current_step = content
        self.thinking_content = content
        self._refresh_display()

    def _update_progress(
        self,
        step: int,
        total: int,
        step_id: str,
        description: str
    ) -> None:
        """Update progress display"""
        self.step_details[step_id] = {
            "status": "in_progress",
            "description": description,
            "step_number": step,
            "total": total,
            "details": None,
            "expanded": False
        }
        self._refresh_display()

    def _mark_complete(self, step_id: str) -> None:
        """Mark step as complete with checkmark"""
        if step_id in self.step_details:
            self.step_details[step_id]["status"] = "completed"
            completed_list = list(self.completed_steps)
            completed_list.append(step_id)
            self.completed_steps = completed_list
        self._refresh_display()

    def _show_error(self, content: str) -> None:
        """Show error message and mark current step as error"""
        # Mark any in-progress step as error
        for step_id, step_data in self.step_details.items():
            if step_data["status"] == "in_progress":
                step_data["status"] = "error"
                step_data["error"] = content
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Rebuild the display with current state"""
        lines = []

        # Header
        lines.append("[bold indigo]💭 Agent Thinking Process[/bold indigo]")
        lines.append("")
        lines.append("[dim]-------------------------------------------[/dim]")

        # Current thinking (with pulsing animation)
        if self.current_step:
            lines.append(f"[indigo]➜ {self.current_step}[/indigo]")
            lines.append("")

        # Step list with checkmarks
        if self.step_details:
            sorted_steps = sorted(
                self.step_details.keys(),
                key=lambda x: self.step_details[x].get("step_number", 0)
            )

            for step_id in sorted_steps:
                step_data = self.step_details[step_id]
                status = step_data.get("status", "pending")
                description = step_data.get("description", "")
                step_num = step_data.get("step_number", 0)
                total = step_data.get("total", 0)

                # Select icon based on status
                if status == "completed":
                    icon = "[green]✓[/green]"
                elif status == "in_progress":
                    icon = "[yellow]⏳[/yellow]"
                elif status == "error":
                    icon = "[red]✗[/red]"
                else:
                    icon = "[ ]"

                # Build step line
                if total > 0:
                    lines.append(f"{icon} {step_num}/{total}. {description}")
                else:
                    lines.append(f"{icon} {description}")

                # Show details if expanded
                if step_data.get("expanded") and step_data.get("details"):
                    for detail in step_data["details"]:
                        lines.append(f"   [dim]{detail}[/dim]")

                # Show error if present
                if status == "error" and step_data.get("error"):
                    lines.append(f"   [red]Error: {step_data['error']}[/red]")

        # Update widget content
        self.update("\n".join(lines) if lines else "[dim italic]에이전트가 사고 중입니다...[/dim italic]")

    def render(self) -> str:
        """패널 렌더링"""
        if not self.thinking_content and not self.steps and not self.step_details:
            return "[dim italic]에이전트가 사고 중입니다...[/dim italic]"

        lines = ["[bold]💭 Agent Thinking[/bold]"]

        if self.thinking_content:
            lines.append(f"\n{self.thinking_content}")

        if self.steps:
            lines.append("\n[bold]Steps:[/bold]")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def on_click(self, event) -> None:
        """Toggle step details on click (future enhancement)"""
        # TODO: Detect which step was clicked and toggle expanded state
        # This would require more sophisticated coordinate tracking
        pass

    def update_thinking(self, content: str):
        """사고 내용 업데이트 (backward compatibility)"""
        self.thinking_content = content

    def add_step(self, step: str):
        """추론 단계 추가 (backward compatibility)"""
        new_steps = list(self.steps)
        new_steps.append(step)
        self.steps = new_steps[-5:]  # 최근 5개만 유지

    def clear(self):
        """내용 초기화"""
        self.thinking_content = ""
        self.steps = []
        self.current_step = None
        self.completed_steps = []
        self.step_details = {}


class StreamingMessageView(Static):
    """
    스트리밍 메시지 뷰 - 실시간으로 토큰이 추가됨
    """
    
    DEFAULT_CSS = """
    StreamingMessageView {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: #000000;
        border-left: thick #4f46e5;
        margin-bottom: 1;
    }
    
    .streaming-header {
        color: #4f46e5;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .streaming-content {
        color: #e2e8f0;
    }
    
    .streaming-cursor {
        background: #4f46e5;
        color: #000000;
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
