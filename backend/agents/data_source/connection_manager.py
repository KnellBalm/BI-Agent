import os
import json
import sqlite3
import datetime
import logging
import re
from typing import Dict, Any, Optional, List
import pandas as pd
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

# Initialize localized logger
logger = setup_logger("connection_manager", "connections.log")

class ConnectionManager:
    """
    Manages connections to various data sources.
    Uses a local registry (connections.json) for persisting connection details.
    """
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.project_dir = path_manager.get_project_path(project_id)
        self.registry_path = self.project_dir / "connections.json"
        self._ensure_registry_exists()
        self.active_sessions: Dict[str, Any] = {}
        logger.info(f"ConnectionManager initialized for project '{project_id}' at {self.registry_path}")
        
        # Auto-onboarding: Create sample if registry is empty
        self._auto_onboard_sample()

    def _auto_onboard_sample(self):
        """Checks if registry is empty and adds a sample SQLite source if needed."""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            if not registry:
                logger.info(f"Empty registry for project '{self.project_id}'. Auto-onboarding sample sales data.")
                # We keep the source data in the package for demo, or move to ~/.bi-agent
                source_path = path_manager.get_project_path(self.project_id) / "sample_sales.sqlite"
                
                # Check if file exists, if not generate it
                if not os.path.exists(source_path):
                    from backend.utils.sample_data_gen import generate_sample_sqlite
                    generate_sample_sqlite(str(source_path))
                    logger.info(f"Generated sample database at {source_path}")
                
                self.register_connection(
                    conn_id="sample_sales",
                    conn_type="sqlite",
                    config={"path": str(source_path)},
                    name="Sample Sales Data (Auto)",
                    category="Demo"
                )
        except Exception as e:
            logger.error(f"Auto-onboarding failed: {e}")

    def _ensure_registry_exists(self):
        """Creates config directory and empty registry file if not exists."""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            if not os.path.exists(self.registry_path):
                with open(self.registry_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                logger.info(f"Created new connection registry at {self.registry_path}")
        except Exception as e:
            logger.error(f"Failed to ensure registry existence: {e}")

    def register_connection(self, conn_id: str, conn_type: str, config: Dict[str, Any], name: str = "", category: str = "DB"):
        """Registers a new connection configuration after validation."""
        allowed_types = ["sqlite", "postgres", "mysql", "snowflake", "bigquery", "excel", "duckdb"]
        if conn_type not in allowed_types:
            logger.error(f"Unsupported connection type attempted: {conn_type}")
            raise ValueError(f"Unsupported connection type: {conn_type}. Valid types: {allowed_types}")

        # Basic Pre-flight check before registration
        self._validate_config(conn_type, config)

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            registry[conn_id] = {
                "type": conn_type,
                "name": name or conn_id,
                "category": category,
                "config": config,
                "created_at": datetime.datetime.now().isoformat(),
                "last_accessed": None
            }
            
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2)
            
            logger.info(f"Successfully registered connection: {conn_id} ({conn_type})")
            return conn_id
        except Exception as e:
            logger.error(f"Failed to register connection {conn_id}: {e}")
            raise RuntimeError(f"Registration failed: {e}")

    def _validate_config(self, conn_type: str, config: Dict[str, Any]):
        """Performs pre-flight validation on the provided configuration."""
        if conn_type in ["sqlite", "excel", "duckdb"]:
            path = config.get("path")
            if not path:
                raise ValueError("Path is required for file-based connections.")
            if not os.path.isabs(path):
                # We allow relative paths but log a warning if they are ambiguous
                logger.debug(f"Relative path used for {conn_type}: {path}")
        elif conn_type in ["postgres", "mysql"]:
            required = ["host", "dbname", "user"]
            missing = [r for r in required if r not in config]
            if missing:
                raise ValueError(f"Missing required connection parameters: {missing}")

    def get_connection(self, conn_id: str):
        """Retrieves an active connection session or initializes a new one."""
        if conn_id in self.active_sessions:
            return self.active_sessions[conn_id]

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            if conn_id not in registry:
                logger.error(f"Requested connection ID '{conn_id}' not found in registry.")
                raise ValueError(f"Connection ID '{conn_id}' is not registered.")
            
            conn_info = registry[conn_id]
            conn_type = conn_info["type"]
            config = self._inject_env_vars(conn_info["config"])
            
            session = self._initialize_session(conn_type, config)
            self.active_sessions[conn_id] = session

            # Update last_accessed timestamp
            conn_info["last_accessed"] = datetime.datetime.now().isoformat()
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2)

            logger.info(f"Initialized active session for {conn_id}")
            return session
        except Exception as e:
            logger.error(f"Error getting connection {conn_id}: {e}")
            raise

    def _initialize_session(self, conn_type: str, config: Dict[str, Any]):
        """Initializes a connection session with error handling."""
        try:
            if conn_type == "sqlite":
                path = config["path"]
                if not os.path.exists(path) and path != ":memory:":
                    logger.warning(f"SQLite file not found at {path}. A new one will be created upon use.")
                return sqlite3.connect(path)
            elif conn_type == "excel":
                if not os.path.exists(config["path"]):
                    raise FileNotFoundError(f"Excel file not found: {config['path']}")
                return config["path"]
            elif conn_type == "postgres":
                import psycopg2
                return psycopg2.connect(**config)
            elif conn_type == "duckdb":
                import duckdb
                path = config["path"]
                return duckdb.connect(database=path)
            else:
                raise NotImplementedError(f"Connection type '{conn_type}' is not supported yet.")
        except Exception as e:
            logger.error(f"Failed to initialize {conn_type} session: {e}")
            raise RuntimeError(f"Session initialization failed: {e}")

    def run_query(self, conn_id: str, query: str) -> pd.DataFrame:
        """Runs a SQL query with robust error handling and monitoring."""
        try:
            session = self.get_connection(conn_id)
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            conn_type = registry[conn_id]["type"]
            
            start_time = datetime.datetime.now()
            if conn_type in ["sqlite", "postgres"]:
                df = pd.read_sql_query(query, session)
            elif conn_type == "duckdb":
                df = session.execute(query).df()
            elif conn_type == "excel":
                df = pd.read_excel(session)
            else:
                raise ValueError(f"Cannot run query on connection type '{conn_type}'")
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Query executed on {conn_id} in {duration:.4f}s. Rows: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"Query failed on {conn_id}: {e}")
            raise RuntimeError(f"Query execution failed: {e}")

    def _inject_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces ${VAR} placeholders with environment variables."""
        new_config = {}
        for k, v in config.items():
            if isinstance(v, str):
                matches = re.findall(r"\${(\w+)}", v)
                for var in matches:
                    env_val = os.getenv(var, "")
                    if not env_val:
                        logger.warning(f"Environment variable {var} is not set.")
                    v = v.replace(f"${{{var}}}", env_val)
            new_config[k] = v
        return new_config

    def close_all(self):
        """Cleanly closes all active sessions."""
        for conn_id, session in self.active_sessions.items():
            try:
                if hasattr(session, 'close'):
                    session.close()
                logger.info(f"Closed session for {conn_id}")
            except Exception as e:
                logger.error(f"Error closing session for {conn_id}: {e}")
        self.active_sessions.clear()
