"""
Query History Management for BI-Agent Console

Provides query execution history persistence and analysis for database queries.
Tracks execution metrics, errors, and connection context for debugging and auditing.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class QueryHistoryEntry:
    """Represents a single query execution with metadata and metrics."""
    query: str
    timestamp: str  # ISO format datetime string
    connection_id: str
    execution_time_ms: float
    row_count: int
    status: str  # "success" or "error"
    error_message: Optional[str] = None
    id: Optional[str] = None  # Unique identifier, auto-generated if None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'QueryHistoryEntry':
        """Create instance from dictionary."""
        return cls(**data)


class QueryHistory:
    """
    Manages query execution history for BI-Agent console.

    Features:
    - Persistent storage across sessions
    - Execution metrics tracking (time, rows, errors)
    - Connection-based filtering
    - Automatic cleanup of old entries
    - Maximum size limit (default: 1000)
    - Auto-cleanup after 90 days
    """

    def __init__(
        self,
        history_file: Optional[Path] = None,
        max_entries: int = 1000,
        auto_cleanup_days: int = 90
    ):
        """
        Initialize query history.

        Args:
            history_file: Path to history JSON file. Defaults to ~/.bi-agent/query_history.json
            max_entries: Maximum number of queries to keep in history
            auto_cleanup_days: Automatically remove entries older than this many days
        """
        if history_file is None:
            history_file = Path.home() / ".bi-agent" / "query_history.json"

        self.history_file = history_file
        self.max_entries = max_entries
        self.auto_cleanup_days = auto_cleanup_days
        self.entries: List[QueryHistoryEntry] = []

        # Ensure directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        self.load()

        # Auto-cleanup old entries on initialization
        self.clear_old_entries(self.auto_cleanup_days)

        logger.info(
            f"QueryHistory initialized: {len(self.entries)} entries loaded from {self.history_file}"
        )

    def load(self) -> None:
        """Load query history from JSON file."""
        if not self.history_file.exists():
            logger.debug(f"History file not found, starting fresh: {self.history_file}")
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load entries
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        self.entries.append(QueryHistoryEntry.from_dict(item))

            # Enforce max size
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]

            logger.info(f"Loaded {len(self.entries)} queries from history")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse history file: {e}. Starting fresh.")
            self.entries = []
        except Exception as e:
            logger.error(f"Error loading history: {e}. Starting fresh.")
            self.entries = []

    def save(self) -> None:
        """Save query history to JSON file."""
        try:
            # Convert entries to dict format
            data = [entry.to_dict() for entry in self.entries]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved {len(self.entries)} queries to history")

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add_entry(self, entry: QueryHistoryEntry) -> None:
        """
        Add a query execution entry to history.

        Args:
            entry: QueryHistoryEntry instance to add
        """
        # Generate ID if not provided
        if entry.id is None:
            entry.id = str(uuid.uuid4())

        self.entries.append(entry)

        # Enforce max size
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        # Persist to disk
        self.save()

        logger.debug(
            f"Added to query history: {entry.status} query on {entry.connection_id} "
            f"({entry.execution_time_ms:.2f}ms, {entry.row_count} rows)"
        )

    def get_recent(self, limit: int = 50) -> List[QueryHistoryEntry]:
        """
        Get most recent query entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of QueryHistoryEntry objects, most recent first
        """
        return list(reversed(self.entries[-limit:]))

    def get_by_connection(self, connection_id: str) -> List[QueryHistoryEntry]:
        """
        Get all queries for a specific connection.

        Args:
            connection_id: Connection identifier to filter by

        Returns:
            List of QueryHistoryEntry objects for the connection, most recent first
        """
        connection_entries = [
            entry for entry in self.entries
            if entry.connection_id == connection_id
        ]
        return list(reversed(connection_entries))

    def clear_old_entries(self, days: int) -> int:
        """
        Remove query entries older than specified number of days.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        if days <= 0:
            logger.warning("Invalid days value for cleanup, skipping")
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        initial_count = len(self.entries)

        # Filter out old entries
        filtered_entries = []
        for entry in self.entries:
            try:
                if datetime.fromisoformat(entry.timestamp) >= cutoff_date:
                    filtered_entries.append(entry)
            except (ValueError, TypeError):
                # Skip entries with malformed timestamps
                logger.warning(f"Skipped entry with malformed timestamp: {entry.timestamp}")
        self.entries = filtered_entries

        removed_count = initial_count - len(self.entries)

        if removed_count > 0:
            self.save()
            logger.info(f"Removed {removed_count} entries older than {days} days")

        return removed_count

    def clear(self) -> None:
        """Clear all query history."""
        self.entries = []
        self.save()
        logger.info("Query history cleared")


# Singleton instance for application-wide use
_instance: Optional[QueryHistory] = None


def get_query_history(
    max_entries: int = 1000,
    auto_cleanup_days: int = 90
) -> QueryHistory:
    """
    Get the global QueryHistory instance (singleton pattern).

    Args:
        max_entries: Maximum entries to keep (only used on first initialization)
        auto_cleanup_days: Auto-cleanup threshold (only used on first initialization)

    Returns:
        The global QueryHistory instance
    """
    global _instance
    if _instance is None:
        _instance = QueryHistory(
            max_entries=max_entries,
            auto_cleanup_days=auto_cleanup_days
        )
    return _instance
