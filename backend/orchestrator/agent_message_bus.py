"""
Agent Message Bus for BI-Agent

Async message bus for agent-to-agent and agent-to-TUI communication.
Uses asyncio.Queue for thread-safe message passing without external dependencies.
Integrates with Textual's worker pattern for UI updates.
"""

import asyncio
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from enum import Enum
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be sent through the message bus."""
    THINKING = "thinking"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    INSIGHT = "insight"
    ERROR = "error"
    PROGRESS = "progress"
    COMPLETE = "complete"


@dataclass
class AgentMessage:
    """
    Message sent between agents or from agents to TUI.

    Attributes:
        timestamp: When the message was created
        from_agent: Source agent ("DataMaster", "Strategist", "Designer", "System")
        to_agent: Target agent or "broadcast" for all subscribers
        message_type: Type of message
        content: Korean message content
        metadata: Additional structured data
    """
    timestamp: datetime
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['message_type'] = self.message_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """
        Parse message from dictionary.

        Args:
            data: Dictionary representation of message

        Returns:
            AgentMessage instance
        """
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            from_agent=data['from_agent'],
            to_agent=data['to_agent'],
            message_type=MessageType(data['message_type']),
            content=data['content'],
            metadata=data.get('metadata', {})
        )


class AgentMessageBus:
    """
    Async message bus for agent-to-agent and agent-to-TUI communication.

    Uses asyncio.Queue for thread-safe message passing without external dependencies.
    Integrates with Textual's worker pattern for UI updates.

    Example:
        # In bi_agent_console.py
        from backend.orchestrator.agent_message_bus import AgentMessageBus

        def on_mount(self) -> None:
            bus = AgentMessageBus()
            bus.subscribe(self._handle_agent_message)
            asyncio.create_task(bus.start())

        def _handle_agent_message(self, message: AgentMessage) -> None:
            # Update UI based on message type
            if message.message_type == MessageType.THINKING:
                self.update_thinking_panel(message.content)
            elif message.message_type == MessageType.PROGRESS:
                self.update_progress_bar(
                    message.metadata['step'],
                    message.metadata['total']
                )
    """

    _instance: Optional['AgentMessageBus'] = None

    def __new__(cls):
        """Singleton pattern - only one message bus instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize message bus if not already initialized."""
        if self._initialized:
            return
        self._queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._subscribers: List[Callable[[AgentMessage], None]] = []
        self._running = False
        self._log_path = Path("logs/agent_messages.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        logger.info("AgentMessageBus initialized")

    def subscribe(self, callback: Callable[[AgentMessage], None]) -> None:
        """
        Subscribe to all messages.

        Args:
            callback: Function to call when a message is received.
                     Should accept an AgentMessage parameter.
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            logger.info(f"Subscriber added. Total subscribers: {len(self._subscribers)}")

    def unsubscribe(self, callback: Callable[[AgentMessage], None]) -> None:
        """
        Unsubscribe from messages.

        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.info(f"Subscriber removed. Total subscribers: {len(self._subscribers)}")

    async def publish(self, message: AgentMessage) -> None:
        """
        Publish message to all subscribers.

        Args:
            message: Message to publish
        """
        try:
            await self._queue.put(message)

            # Log to file
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")

            logger.debug(f"Message published: {message.message_type.value} from {message.from_agent}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}", exc_info=True)

    async def start(self) -> None:
        """
        Start message dispatch loop.

        This should be run as an asyncio task. It will continuously
        process messages from the queue and dispatch them to subscribers.
        """
        self._running = True
        logger.info("AgentMessageBus started")

        while self._running:
            try:
                # Wait for message with timeout to allow checking _running flag
                message = await asyncio.wait_for(self._queue.get(), timeout=0.1)

                # Dispatch to all subscribers
                for subscriber in self._subscribers:
                    try:
                        # Call subscriber synchronously
                        # If subscriber needs async, it should schedule its own task
                        subscriber(message)
                    except Exception as e:
                        logger.error(
                            f"Subscriber error for {message.message_type.value}: {e}",
                            exc_info=True
                        )

            except asyncio.TimeoutError:
                # No message available, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in message dispatch loop: {e}", exc_info=True)

        logger.info("AgentMessageBus stopped")

    def stop(self) -> None:
        """Stop message dispatch loop."""
        self._running = False
        logger.info("AgentMessageBus stop requested")

    def clear_log(self) -> None:
        """Clear message log file."""
        try:
            if self._log_path.exists():
                self._log_path.unlink()
                logger.info("Message log cleared")
        except Exception as e:
            logger.error(f"Failed to clear message log: {e}", exc_info=True)

    def get_message_history(self, limit: int = 100) -> List[AgentMessage]:
        """
        Get recent messages from log.

        Args:
            limit: Maximum number of messages to return (from end of file)

        Returns:
            List of AgentMessage objects, newest first
        """
        messages = []

        try:
            if not self._log_path.exists():
                return messages

            with open(self._log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines

            # Parse each line
            for line in recent_lines:
                try:
                    data = json.loads(line.strip())
                    messages.append(AgentMessage.from_dict(data))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse message log line: {e}")
                    continue

            # Return newest first
            messages.reverse()

        except Exception as e:
            logger.error(f"Failed to read message history: {e}", exc_info=True)

        return messages

    @property
    def is_running(self) -> bool:
        """Check if message bus is currently running."""
        return self._running

    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self._subscribers)

    def get_queue_size(self) -> int:
        """Get number of messages waiting in queue."""
        return self._queue.qsize()


# Helper functions for common message types

def create_thinking_message(agent: str, content: str, **metadata) -> AgentMessage:
    """
    Helper to create THINKING message.

    Args:
        agent: Name of the agent sending the message
        content: Korean description of what the agent is thinking
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for thinking status

    Example:
        msg = create_thinking_message("DataMaster", "스키마 분석 중...")
        await bus.publish(msg)
    """
    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent="broadcast",
        message_type=MessageType.THINKING,
        content=content,
        metadata=metadata
    )


def create_progress_message(
    agent: str,
    step: int,
    total: int,
    description: str,
    **metadata
) -> AgentMessage:
    """
    Helper to create PROGRESS message.

    Args:
        agent: Name of the agent sending the message
        step: Current step number (1-indexed)
        total: Total number of steps
        description: Korean description of current step
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for progress update

    Example:
        msg = create_progress_message("Strategist", 2, 5, "가설 검증 중")
        await bus.publish(msg)
    """
    metadata_dict = {
        "step": step,
        "total": total,
        "description": description,
        **metadata
    }

    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent="broadcast",
        message_type=MessageType.PROGRESS,
        content=f"{step}/{total} 단계: {description}",
        metadata=metadata_dict
    )


def create_error_message(
    agent: str,
    error: str,
    error_type: Optional[str] = None,
    **metadata
) -> AgentMessage:
    """
    Helper to create ERROR message.

    Args:
        agent: Name of the agent sending the message
        error: Error message in Korean
        error_type: Optional error classification
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for error notification
    """
    metadata_dict = {"error_type": error_type, **metadata} if error_type else metadata

    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent="broadcast",
        message_type=MessageType.ERROR,
        content=error,
        metadata=metadata_dict
    )


def create_insight_message(
    agent: str,
    insight: str,
    confidence: Optional[float] = None,
    **metadata
) -> AgentMessage:
    """
    Helper to create INSIGHT message.

    Args:
        agent: Name of the agent sending the message
        insight: Insight text in Korean
        confidence: Optional confidence score (0.0-1.0)
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for insight notification
    """
    metadata_dict = {"confidence": confidence, **metadata} if confidence else metadata

    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent="broadcast",
        message_type=MessageType.INSIGHT,
        content=insight,
        metadata=metadata_dict
    )


def create_data_request_message(
    agent: str,
    query: str,
    target_agent: str = "DataMaster",
    **metadata
) -> AgentMessage:
    """
    Helper to create DATA_REQUEST message.

    Args:
        agent: Name of the agent requesting data
        query: Data request description
        target_agent: Agent to handle the request
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for data request
    """
    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent=target_agent,
        message_type=MessageType.DATA_REQUEST,
        content=query,
        metadata=metadata
    )


def create_data_response_message(
    agent: str,
    response: str,
    target_agent: str,
    data: Optional[Dict[str, Any]] = None,
    **metadata
) -> AgentMessage:
    """
    Helper to create DATA_RESPONSE message.

    Args:
        agent: Name of the agent responding
        response: Response description
        target_agent: Agent that requested the data
        data: Optional structured data payload
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for data response
    """
    metadata_dict = {"data": data, **metadata} if data else metadata

    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent=target_agent,
        message_type=MessageType.DATA_RESPONSE,
        content=response,
        metadata=metadata_dict
    )


def create_complete_message(
    agent: str,
    summary: str,
    **metadata
) -> AgentMessage:
    """
    Helper to create COMPLETE message.

    Args:
        agent: Name of the agent completing work
        summary: Completion summary in Korean
        **metadata: Additional metadata to include

    Returns:
        AgentMessage configured for completion notification
    """
    return AgentMessage(
        timestamp=datetime.now(),
        from_agent=agent,
        to_agent="broadcast",
        message_type=MessageType.COMPLETE,
        content=summary,
        metadata=metadata
    )
