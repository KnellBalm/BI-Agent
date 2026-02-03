"""
BI-Agent Orchestrator Package - Facade Pattern for Backward Compatibility
"""

from .managers.auth_manager import auth_manager, AuthManager
from .managers.connection_manager import ConnectionManager
from .managers.quota_manager import quota_manager, QuotaManager
from .managers.context_manager import context_manager
from .managers.command_history import CommandHistory
from .providers.llm_provider import LLMProvider, GeminiProvider, OllamaProvider, FailoverLLMProvider
from .orchestrators.base_orchestrator import AbstractOrchestrator
from .orchestrators.graph_orchestrator import Orchestrator
from .orchestrators.collaborative_orchestrator import CollaborativeOrchestrator
from .orchestrators.interaction_orchestrator import InteractionOrchestrator
from .messaging.agent_message_bus import AgentMessageBus
from .ui.components.hud_statusline import HUDStatusLine
from .ui.components.error_viewer_screen import ErrorViewerScreen
from .ui.components.thinking_translator import ThinkingTranslator
from .ui.components.interaction_ui import InteractionUI
from .ui.components.message_components import (
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker
)
from .ui.views.dashboard_view import DashboardView

__all__ = [
    "auth_manager",
    "AuthManager",
    "ConnectionManager",
    "quota_manager",
    "QuotaManager",
    "context_manager",
    "CommandHistory",
    "LLMProvider",
    "GeminiProvider",
    "OllamaProvider",
    "FailoverLLMProvider",
    "AbstractOrchestrator",
    "Orchestrator",
    "CollaborativeOrchestrator",
    "InteractionOrchestrator",
    "AgentMessageBus",
    "HUDStatusLine",
    "ErrorViewerScreen",
    "ThinkingTranslator",
    "InteractionUI",
    "MessageBubble",
    "ThinkingPanel",
    "StreamingMessageView",
    "ToolActivityTracker",
    "DashboardView"
]
