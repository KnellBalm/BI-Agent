"""
Command History Management for BI-Agent Console

Provides command history persistence and navigation for terminal-style UX.
Supports up/down arrow navigation and tab completion for Korean BI phrases.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommandHistoryEntry:
    """Represents a single command in history with metadata."""
    command: str
    timestamp: str  # ISO format datetime string
    context: str = ""  # Optional context like intent type or command category

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CommandHistoryEntry':
        """Create instance from dictionary."""
        return cls(**data)


class CommandHistory:
    """
    Manages command history for BI-Agent console.

    Features:
    - Persistent storage across sessions
    - Up/Down arrow navigation
    - Tab completion suggestions
    - Maximum size limit (default: 100)
    - Common Korean BI phrase completion
    """

    # Common Korean BI analysis phrases for tab completion
    COMMON_PHRASES = [
        "매출",
        "매출 분석",
        "매출 추이",
        "분석",
        "추이",
        "추이 분석",
        "성능",
        "성능 분석",
        "고객",
        "고객 분석",
        "고객 세그먼트",
        "제품",
        "제품 분석",
        "제품별 매출",
        "월별",
        "월별 매출",
        "월별 추이",
        "지역",
        "지역별 매출",
        "지역별 분석",
        "연도별",
        "분기별",
        "일별",
        "카테고리별",
        "상위",
        "하위",
        "비교",
        "증감",
        "성장률",
        "점유율",
    ]

    def __init__(
        self,
        history_file: Optional[Path] = None,
        max_size: int = 100
    ):
        """
        Initialize command history.

        Args:
            history_file: Path to history JSON file. Defaults to ~/.bi-agent/history.json
            max_size: Maximum number of commands to keep in history
        """
        if history_file is None:
            history_file = Path.home() / ".bi-agent" / "history.json"

        self.history_file = history_file
        self.max_size = max_size
        self.entries: List[CommandHistoryEntry] = []
        self.navigation_index: Optional[int] = None  # Current position in history navigation

        # Ensure directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        self._load_history()

        logger.info(
            f"CommandHistory initialized: {len(self.entries)} entries loaded from {self.history_file}"
        )

    def _load_history(self) -> None:
        """Load command history from JSON file."""
        if not self.history_file.exists():
            logger.debug(f"History file not found, starting fresh: {self.history_file}")
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Support both old list format and new structured format
            if isinstance(data, list):
                # Old format: just list of strings or dicts
                for item in data:
                    if isinstance(item, str):
                        # Legacy: just command string
                        self.entries.append(CommandHistoryEntry(
                            command=item,
                            timestamp=datetime.now().isoformat()
                        ))
                    elif isinstance(item, dict):
                        # New format
                        self.entries.append(CommandHistoryEntry.from_dict(item))

            # Enforce max size
            if len(self.entries) > self.max_size:
                self.entries = self.entries[-self.max_size:]

            logger.info(f"Loaded {len(self.entries)} commands from history")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse history file: {e}. Starting fresh.")
            self.entries = []
        except Exception as e:
            logger.error(f"Error loading history: {e}. Starting fresh.")
            self.entries = []

    def _save_history(self) -> None:
        """Save command history to JSON file."""
        try:
            # Convert entries to dict format
            data = [entry.to_dict() for entry in self.entries]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved {len(self.entries)} commands to history")

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add_command(self, command: str, context: str = "") -> None:
        """
        Add a command to history.

        Args:
            command: The command string to add
            context: Optional context (e.g., "intent", "query", "slash_command")
        """
        if not command or not command.strip():
            return

        command = command.strip()

        # Avoid consecutive duplicates
        if self.entries and self.entries[-1].command == command:
            logger.debug("Skipping duplicate consecutive command")
            return

        entry = CommandHistoryEntry(
            command=command,
            timestamp=datetime.now().isoformat(),
            context=context
        )

        self.entries.append(entry)

        # Enforce max size
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]

        # Reset navigation index
        self.navigation_index = None

        # Persist to disk
        self._save_history()

        logger.debug(f"Added to history: '{command}' (context: {context})")

    def get_previous(self) -> Optional[str]:
        """
        Navigate backward in history (up arrow).

        Returns:
            Previous command string, or None if at the beginning
        """
        if not self.entries:
            return None

        # First time navigating - start at the end
        if self.navigation_index is None:
            self.navigation_index = len(self.entries) - 1
        else:
            # Move backwards if possible
            if self.navigation_index > 0:
                self.navigation_index -= 1
            else:
                # Already at the beginning
                return self.entries[0].command

        return self.entries[self.navigation_index].command

    def get_next(self) -> Optional[str]:
        """
        Navigate forward in history (down arrow).

        Returns:
            Next command string, or empty string if at the end
        """
        if not self.entries or self.navigation_index is None:
            return ""

        # Move forward
        if self.navigation_index < len(self.entries) - 1:
            self.navigation_index += 1
            return self.entries[self.navigation_index].command
        else:
            # At the end - reset navigation and return empty
            self.navigation_index = None
            return ""

    def get_all(self) -> List[CommandHistoryEntry]:
        """
        Get all history entries.

        Returns:
            List of all CommandHistoryEntry objects
        """
        return self.entries.copy()

    def get_suggestions(self, prefix: str) -> List[str]:
        """
        Get command suggestions based on prefix.

        Combines:
        1. Commands from history that start with prefix
        2. Common Korean BI phrases that start with prefix

        Args:
            prefix: The prefix to match against

        Returns:
            List of matching commands/phrases, sorted by relevance
        """
        if not prefix:
            return []

        prefix = prefix.strip()
        suggestions = []

        # Get matching commands from history (most recent first)
        history_matches = []
        for entry in reversed(self.entries):
            if entry.command.startswith(prefix) and entry.command not in history_matches:
                history_matches.append(entry.command)

        # Get matching common phrases
        phrase_matches = [
            phrase for phrase in self.COMMON_PHRASES
            if phrase.startswith(prefix) and phrase not in history_matches
        ]

        # Combine: history first (user's actual commands are more relevant)
        suggestions = history_matches + phrase_matches

        # Limit to reasonable number
        return suggestions[:10]

    def clear(self) -> None:
        """Clear all history."""
        self.entries = []
        self.navigation_index = None
        self._save_history()
        logger.info("Command history cleared")

    def reset_navigation(self) -> None:
        """Reset navigation index (call when user starts typing)."""
        self.navigation_index = None


# Singleton instance for application-wide use
_instance: Optional[CommandHistory] = None


def get_command_history() -> CommandHistory:
    """
    Get the global CommandHistory instance (singleton pattern).

    Returns:
        The global CommandHistory instance
    """
    global _instance
    if _instance is None:
        _instance = CommandHistory()
    return _instance
