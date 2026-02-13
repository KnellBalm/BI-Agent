"""
Query Bookmarks Manager

Manages query bookmarks with versioning support, tags, and JSON persistence.
Provides functionality to add, update, delete, and search bookmarks across
multiple database connections.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid
import logging

from backend.orchestrator.config.explorer_config import get_config, BookmarkConfig

logger = logging.getLogger(__name__)


# Singleton instance
_bookmarks_instance: Optional['QueryBookmarks'] = None


def get_query_bookmarks(storage_path: Optional[Path] = None) -> 'QueryBookmarks':
    """
    Get or create the global QueryBookmarks instance.

    Args:
        storage_path: Optional custom storage path.

    Returns:
        QueryBookmarks singleton instance.
    """
    global _bookmarks_instance

    if _bookmarks_instance is None:
        _bookmarks_instance = QueryBookmarks(storage_path=storage_path)

    return _bookmarks_instance


@dataclass
class QueryVersion:
    """Represents a versioned query snapshot."""
    query: str
    timestamp: str
    version_number: int


@dataclass
class QueryBookmark:
    """Represents a saved query bookmark with metadata and version history."""
    id: str
    name: str
    query: str
    tags: List[str]
    created_at: str
    modified_at: str
    versions: List[QueryVersion]
    connection_ids: List[str]


class QueryBookmarks:
    """
    Manager for query bookmarks with versioning and persistence.

    Features:
    - UUID-based bookmark identification
    - Version history with configurable limits
    - Tag-based organization
    - Connection-scoped bookmarks
    - Keyword search across name and query
    - JSON file persistence
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize QueryBookmarks manager.

        Args:
            storage_path: Custom storage path. Defaults to ~/.bi-agent/bookmarks.json
        """
        if storage_path is None:
            storage_path = Path.home() / ".bi-agent" / "bookmarks.json"

        self.storage_path = Path(storage_path)
        self.bookmarks: List[QueryBookmark] = []
        self.config = get_config().bookmark

        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing bookmarks
        self.load()

    def add_bookmark(
        self,
        name: str,
        query: str,
        tags: List[str],
        connection_id: str
    ) -> str:
        """
        Add a new query bookmark.

        Args:
            name: Descriptive name for the bookmark
            query: SQL query text
            tags: List of tags for categorization
            connection_id: Associated database connection ID

        Returns:
            UUID string of the created bookmark
        """
        bookmark_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Create initial version
        initial_version = QueryVersion(
            query=query,
            timestamp=now,
            version_number=1
        )

        bookmark = QueryBookmark(
            id=bookmark_id,
            name=name,
            query=query,
            tags=tags,
            created_at=now,
            modified_at=now,
            versions=[initial_version] if self.config.enable_versioning else [],
            connection_ids=[connection_id]
        )

        self.bookmarks.append(bookmark)
        self.save()

        logger.info(f"Added bookmark '{name}' with ID {bookmark_id}")
        return bookmark_id

    def update_bookmark(self, bookmark_id: str, query: str) -> bool:
        """
        Update an existing bookmark's query and add a new version.

        Args:
            bookmark_id: UUID of the bookmark to update
            query: New SQL query text

        Returns:
            True if update succeeded, False if bookmark not found
        """
        bookmark = self._find_bookmark(bookmark_id)
        if not bookmark:
            logger.warning(f"Bookmark {bookmark_id} not found")
            return False

        now = datetime.now().isoformat()
        bookmark.query = query
        bookmark.modified_at = now

        # Add new version if versioning enabled
        if self.config.enable_versioning:
            new_version_number = len(bookmark.versions) + 1
            new_version = QueryVersion(
                query=query,
                timestamp=now,
                version_number=new_version_number
            )
            bookmark.versions.append(new_version)

            # Trim old versions if exceeding max_versions
            if len(bookmark.versions) > self.config.max_versions:
                bookmark.versions = bookmark.versions[-self.config.max_versions:]
                # Renumber versions after trimming
                for idx, version in enumerate(bookmark.versions, start=1):
                    version.version_number = idx

        self.save()
        logger.info(f"Updated bookmark {bookmark_id}")
        return True

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark by ID.

        Args:
            bookmark_id: UUID of the bookmark to delete

        Returns:
            True if deletion succeeded, False if bookmark not found
        """
        initial_count = len(self.bookmarks)
        self.bookmarks = [b for b in self.bookmarks if b.id != bookmark_id]

        if len(self.bookmarks) < initial_count:
            self.save()
            logger.info(f"Deleted bookmark {bookmark_id}")
            return True

        logger.warning(f"Bookmark {bookmark_id} not found")
        return False

    def get_all(self) -> List[QueryBookmark]:
        """
        Get all bookmarks.

        Returns:
            List of all QueryBookmark objects
        """
        return self.bookmarks.copy()

    def get_by_tag(self, tag: str) -> List[QueryBookmark]:
        """
        Get bookmarks filtered by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of QueryBookmark objects matching the tag
        """
        return [b for b in self.bookmarks if tag in b.tags]

    def get_by_connection(self, connection_id: str) -> List[QueryBookmark]:
        """
        Get bookmarks associated with a specific connection.

        Args:
            connection_id: Database connection ID to filter by

        Returns:
            List of QueryBookmark objects for the connection
        """
        return [b for b in self.bookmarks if connection_id in b.connection_ids]

    def search(self, keyword: str) -> List[QueryBookmark]:
        """
        Search bookmarks by keyword in name or query text.

        Args:
            keyword: Search term (case-insensitive)

        Returns:
            List of QueryBookmark objects matching the keyword
        """
        keyword_lower = keyword.lower()
        return [
            b for b in self.bookmarks
            if keyword_lower in b.name.lower() or keyword_lower in b.query.lower()
        ]

    def save(self) -> None:
        """Persist bookmarks to JSON file."""
        try:
            data = [self._bookmark_to_dict(b) for b in self.bookmarks]
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.bookmarks)} bookmarks to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save bookmarks: {e}")

    def load(self) -> None:
        """Load bookmarks from JSON file."""
        if not self.storage_path.exists():
            logger.debug(f"No bookmarks file found at {self.storage_path}")
            self.bookmarks = []
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.bookmarks = [self._dict_to_bookmark(item) for item in data]
            logger.debug(f"Loaded {len(self.bookmarks)} bookmarks from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load bookmarks: {e}")
            self.bookmarks = []

    def _find_bookmark(self, bookmark_id: str) -> Optional[QueryBookmark]:
        """Find a bookmark by ID."""
        for bookmark in self.bookmarks:
            if bookmark.id == bookmark_id:
                return bookmark
        return None

    @staticmethod
    def _bookmark_to_dict(bookmark: QueryBookmark) -> dict:
        """Convert QueryBookmark to dictionary for JSON serialization."""
        return {
            "id": bookmark.id,
            "name": bookmark.name,
            "query": bookmark.query,
            "tags": bookmark.tags,
            "created_at": bookmark.created_at,
            "modified_at": bookmark.modified_at,
            "versions": [
                {
                    "query": v.query,
                    "timestamp": v.timestamp,
                    "version_number": v.version_number
                }
                for v in bookmark.versions
            ],
            "connection_ids": bookmark.connection_ids
        }

    @staticmethod
    def _dict_to_bookmark(data: dict) -> QueryBookmark:
        """Convert dictionary to QueryBookmark instance."""
        versions = [
            QueryVersion(
                query=v["query"],
                timestamp=v["timestamp"],
                version_number=v["version_number"]
            )
            for v in data.get("versions", [])
        ]

        return QueryBookmark(
            id=data["id"],
            name=data["name"],
            query=data["query"],
            tags=data.get("tags", []),
            created_at=data["created_at"],
            modified_at=data["modified_at"],
            versions=versions,
            connection_ids=data.get("connection_ids", [])
        )
