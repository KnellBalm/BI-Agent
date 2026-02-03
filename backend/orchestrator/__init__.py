"""
BI-Agent Orchestrator Package - Facade Pattern for Backward Compatibility
"""

from .managers.auth_manager import auth_manager, AuthManager
from .managers.quota_manager import quota_manager, QuotaManager
from .managers.context_manager import context_manager
from .managers.command_history import CommandHistory
from .ui.components.hud_statusline import HUDStatusLine
from .ui.components.error_viewer_screen import ErrorViewerScreen
from .ui.components.message_components import (
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker
)

__all__ = [
    "auth_manager",
    "AuthManager",
    "quota_manager",
    "QuotaManager",
    "context_manager",
    "CommandHistory",
    "HUDStatusLine",
    "ErrorViewerScreen",
    "MessageBubble",
    "ThinkingPanel",
    "StreamingMessageView",
    "ToolActivityTracker"
]
