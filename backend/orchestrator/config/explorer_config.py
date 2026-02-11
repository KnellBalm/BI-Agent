"""
Explorer Configuration Module

Loads and manages configuration for Database Explorer features including
text2sql modes, query execution, history, and UI settings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class LocalModeConfig:
    """Configuration for local text2sql mode (Ollama)."""
    ollama_host: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:7b"
    timeout: int = 30
    temperature: float = 0.1
    num_ctx: int = 4096


@dataclass
class APIProviderConfig:
    """Configuration for a specific API provider."""
    model: str
    temperature: float = 0.3
    max_tokens: int = 2048


@dataclass
class APIModeConfig:
    """Configuration for API text2sql mode (Cloud APIs)."""
    gemini: APIProviderConfig = field(default_factory=lambda: APIProviderConfig(
        model="gemini-2.0-flash-exp",
        temperature=0.3,
        max_tokens=2048
    ))
    claude: APIProviderConfig = field(default_factory=lambda: APIProviderConfig(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=2048
    ))
    openai: APIProviderConfig = field(default_factory=lambda: APIProviderConfig(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=2048
    ))


@dataclass
class Text2SQLConfig:
    """Configuration for text2sql functionality."""
    default_mode: str = "local"  # "local" or "api"
    default_api_provider: str = "gemini"  # "gemini", "claude", or "openai"
    local: LocalModeConfig = field(default_factory=LocalModeConfig)
    api: APIModeConfig = field(default_factory=APIModeConfig)


@dataclass
class QueryConfig:
    """Configuration for query execution."""
    max_rows: int = 10000
    timeout: int = 60
    validate_before_run: bool = True


@dataclass
class HistoryConfig:
    """Configuration for query history."""
    max_entries: int = 1000
    auto_cleanup_days: int = 90


@dataclass
class BookmarkConfig:
    """Configuration for query bookmarks."""
    enable_versioning: bool = True
    max_versions: int = 10


@dataclass
class UIConfig:
    """Configuration for UI settings."""
    vim_mode: bool = True
    show_line_numbers: bool = True
    syntax_theme: str = "monokai"
    auto_save_interval: int = 30


@dataclass
class ExplorerConfig:
    """Main explorer configuration."""
    text2sql: Text2SQLConfig = field(default_factory=Text2SQLConfig)
    query: QueryConfig = field(default_factory=QueryConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    bookmark: BookmarkConfig = field(default_factory=BookmarkConfig)
    ui: UIConfig = field(default_factory=UIConfig)


def _build_local_config(data: Dict[str, Any]) -> LocalModeConfig:
    """Build LocalModeConfig from dictionary."""
    return LocalModeConfig(
        ollama_host=data.get("ollama_host", "http://localhost:11434"),
        model=data.get("model", "qwen2.5-coder:7b"),
        timeout=data.get("timeout", 30),
        temperature=data.get("temperature", 0.1),
        num_ctx=data.get("num_ctx", 4096)
    )


def _build_api_provider_config(data: Dict[str, Any]) -> APIProviderConfig:
    """Build APIProviderConfig from dictionary."""
    return APIProviderConfig(
        model=data.get("model", ""),
        temperature=data.get("temperature", 0.3),
        max_tokens=data.get("max_tokens", 2048)
    )


def _build_api_config(data: Dict[str, Any]) -> APIModeConfig:
    """Build APIModeConfig from dictionary."""
    return APIModeConfig(
        gemini=_build_api_provider_config(data.get("gemini", {})),
        claude=_build_api_provider_config(data.get("claude", {})),
        openai=_build_api_provider_config(data.get("openai", {}))
    )


def _build_text2sql_config(data: Dict[str, Any]) -> Text2SQLConfig:
    """Build Text2SQLConfig from dictionary."""
    return Text2SQLConfig(
        default_mode=data.get("default_mode", "local"),
        default_api_provider=data.get("default_api_provider", "gemini"),
        local=_build_local_config(data.get("local", {})),
        api=_build_api_config(data.get("api", {}))
    )


def _build_query_config(data: Dict[str, Any]) -> QueryConfig:
    """Build QueryConfig from dictionary."""
    return QueryConfig(
        max_rows=data.get("max_rows", 10000),
        timeout=data.get("timeout", 60),
        validate_before_run=data.get("validate_before_run", True)
    )


def _build_history_config(data: Dict[str, Any]) -> HistoryConfig:
    """Build HistoryConfig from dictionary."""
    return HistoryConfig(
        max_entries=data.get("max_entries", 1000),
        auto_cleanup_days=data.get("auto_cleanup_days", 90)
    )


def _build_bookmark_config(data: Dict[str, Any]) -> BookmarkConfig:
    """Build BookmarkConfig from dictionary."""
    return BookmarkConfig(
        enable_versioning=data.get("enable_versioning", True),
        max_versions=data.get("max_versions", 10)
    )


def _build_ui_config(data: Dict[str, Any]) -> UIConfig:
    """Build UIConfig from dictionary."""
    return UIConfig(
        vim_mode=data.get("vim_mode", True),
        show_line_numbers=data.get("show_line_numbers", True),
        syntax_theme=data.get("syntax_theme", "monokai"),
        auto_save_interval=data.get("auto_save_interval", 30)
    )


def load_config(config_path: Optional[Path] = None) -> ExplorerConfig:
    """
    Load explorer configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, uses default location.

    Returns:
        ExplorerConfig instance with loaded settings.

    Notes:
        - If config file doesn't exist, returns default configuration
        - Missing sections use sensible defaults
        - Invalid YAML logs warning and returns defaults
    """
    if config_path is None:
        # Default path: backend/config/explorer_config.yaml
        config_path = Path(__file__).parent.parent.parent / "config" / "explorer_config.yaml"

    # Return defaults if file doesn't exist
    if not config_path.exists():
        logger.warning(
            f"Configuration file not found at {config_path}. Using default settings."
        )
        return ExplorerConfig()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            logger.warning("Configuration file is empty. Using default settings.")
            return ExplorerConfig()

        # Build configuration from loaded data
        return ExplorerConfig(
            text2sql=_build_text2sql_config(data.get("text2sql", {})),
            query=_build_query_config(data.get("query", {})),
            history=_build_history_config(data.get("history", {})),
            bookmark=_build_bookmark_config(data.get("bookmark", {})),
            ui=_build_ui_config(data.get("ui", {}))
        )

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}. Using default settings.")
        return ExplorerConfig()
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}. Using default settings.")
        return ExplorerConfig()


# Singleton instance for global access
_config_instance: Optional[ExplorerConfig] = None


def get_config(reload: bool = False) -> ExplorerConfig:
    """
    Get the global explorer configuration instance.

    Args:
        reload: If True, reload configuration from file.

    Returns:
        ExplorerConfig singleton instance.
    """
    global _config_instance

    if _config_instance is None or reload:
        _config_instance = load_config()

    return _config_instance
