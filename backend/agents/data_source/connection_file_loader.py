"""
Connection File Loader
Loads database connections from YAML or JSON configuration files.
Supports environment variable substitution via ${VAR_NAME} pattern.
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("connection_file_loader")


class ConnectionFileLoader:
    """Loads and normalizes connection configurations from YAML/JSON files."""

    @staticmethod
    def load_from_file(filepath: str) -> Dict[str, Dict[str, Any]]:
        """
        Load connections from a YAML or JSON file.

        Args:
            filepath: Path to the connections file (.yaml, .yml, or .json)

        Returns:
            Dictionary mapping connection IDs to connection configs.
            Each config includes: type, host/path, port, database, user, password

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        filepath = Path(filepath).expanduser()
        if not filepath.exists():
            raise FileNotFoundError(f"Connection file not found: {filepath}")

        ext = filepath.suffix.lower()
        if ext in ['.yaml', '.yml']:
            data = ConnectionFileLoader._load_yaml(filepath)
        elif ext == '.json':
            data = ConnectionFileLoader._load_json(filepath)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Use .yaml, .yml, or .json")

        if not ConnectionFileLoader._validate_schema(data):
            raise ValueError("Invalid connection file schema. Must have 'connections' key.")

        connections = data.get('connections', {})
        normalized = {}

        for conn_id, conn_data in connections.items():
            normalized[conn_id] = ConnectionFileLoader._normalize_connection(conn_data)

        return normalized

    @staticmethod
    def _load_yaml(filepath: Path) -> Dict[str, Any]:
        """Load YAML file with environment variable substitution."""
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to load YAML files. "
                "Install it with: pip install pyyaml"
            )

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Substitute environment variables
        content = ConnectionFileLoader._substitute_env_vars(content)

        return yaml.safe_load(content)

    @staticmethod
    def _load_json(filepath: Path) -> Dict[str, Any]:
        """Load JSON file with environment variable substitution."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Substitute environment variables
        content = ConnectionFileLoader._substitute_env_vars(content)

        return json.loads(content)

    @staticmethod
    def _substitute_env_vars(content: str) -> str:
        """
        Replace ${VAR_NAME} patterns with environment variable values.

        Args:
            content: File content string

        Returns:
            Content with environment variables substituted
        """
        import re

        def replacer(match):
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                logger.warning(f"Environment variable ${{{var_name}}} not set, using empty string")
                return ""
            return value

        # Pattern: ${VAR_NAME} or $VAR_NAME
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
        return re.sub(pattern, replacer, content)

    @staticmethod
    def _validate_schema(data: Dict[str, Any]) -> bool:
        """
        Validate that the loaded data has the correct schema.

        Expected format:
        {
            "connections": {
                "conn_id": {
                    "type": "postgres|mysql|sqlite|excel",
                    ...
                }
            }
        }
        """
        if not isinstance(data, dict):
            return False

        if 'connections' not in data:
            return False

        connections = data['connections']
        if not isinstance(connections, dict):
            return False

        # Validate each connection has a 'type' field
        for conn_id, conn_data in connections.items():
            if not isinstance(conn_data, dict):
                logger.error(f"Connection '{conn_id}' must be a dictionary")
                return False
            if 'type' not in conn_data:
                logger.error(f"Connection '{conn_id}' missing required 'type' field")
                return False

        return True

    @staticmethod
    def _normalize_connection(conn_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize connection data for compatibility with ConnectionManager.

        Critical normalization:
        - For postgres/mysql: Ensure both 'database' and 'dbname' keys exist
          (YAML uses 'database', agents ConnectionManager._validate_config expects 'dbname')

        Args:
            conn_data: Raw connection data from file

        Returns:
            Normalized connection data
        """
        normalized = conn_data.copy()

        conn_type = normalized.get('type', '')

        # Field normalization for postgres/mysql (Critic Issue #1 fix)
        if conn_type in ['postgres', 'mysql']:
            # If 'database' exists but 'dbname' doesn't, copy it
            if 'database' in normalized and 'dbname' not in normalized:
                normalized['dbname'] = normalized['database']
            # If 'dbname' exists but 'database' doesn't, copy it (for UI display)
            elif 'dbname' in normalized and 'database' not in normalized:
                normalized['database'] = normalized['dbname']

        return normalized
