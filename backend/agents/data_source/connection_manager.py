"""
Connection Manager Module
Handles various types of data source connections (Postgres, SQLite, Excel, etc.)
and manages connection life-cycles.
"""
import os
import json
import sqlite3
import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import re

class ConnectionManager:
    """
    Manages connections to various data sources.
    Uses a local registry (connections.json) for persisting connection details.
    """
    
    def __init__(self, registry_path: str = "config/connections.json"):
        self.registry_path = registry_path
        self._ensure_registry_exists()
        self.active_sessions: Dict[str, Any] = {}

    def _ensure_registry_exists(self):
        """Creates config directory and empty registry file if not exists."""
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def register_connection(self, conn_id: str, conn_type: str, config: Dict[str, Any], name: str = "", category: str = "DB"):
        """Registers a new connection configuration following the spec."""
        allowed_types = ["sqlite", "postgres", "mysql", "snowflake", "bigquery", "excel"]
        if conn_type not in allowed_types:
            raise ValueError(f"Unsupported connection type: {conn_type}. Valid types: {allowed_types}")

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
        return conn_id

    def _inject_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces ${VAR} placeholders with environment variables."""
        new_config = {}
        for k, v in config.items():
            if isinstance(v, str):
                matches = re.findall(r"\${(\w+)}", v)
                for var in matches:
                    env_val = os.getenv(var, "")
                    v = v.replace(f"${{{var}}}", env_val)
            new_config[k] = v
        return new_config

    def get_connection(self, conn_id: str):
        """Retrieves an active connection session or initializes a new one."""
        if conn_id in self.active_sessions:
            return self.active_sessions[conn_id]

        with open(self.registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        if conn_id not in registry:
            raise ValueError(f"Connection ID '{conn_id}' is not registered.")
        
        conn_info = registry[conn_id]
        conn_type = conn_info["type"]
        config = self._inject_env_vars(conn_info["config"]) # Inject env vars
        
        session = self._initialize_session(conn_type, config)
        self.active_sessions[conn_id] = session

        # Update last_accessed timestamp
        conn_info["last_accessed"] = datetime.datetime.now().isoformat()
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        return session

    def _initialize_session(self, conn_type: str, config: Dict[str, Any]):
        """Initializes a connection session based on type."""
        if conn_type == "sqlite":
            return sqlite3.connect(config["path"])
        elif conn_type == "excel":
            # For Excel, the 'session' will be a list of sheets/metadata or the file path
            return config["path"]
        elif conn_type == "postgres":
            # Real implementation would use psycopg2 or sqlalchemy
            # For now, we simulate returning a stub or connecting if env allows
            try:
                import psycopg2
                return psycopg2.connect(**config)
            except ImportError:
                return "postgres-stub (psycopg2 not installed)"
        else:
            raise NotImplementedError(f"Connection type '{conn_type}' is not supported yet.")

    def run_query(self, conn_id: str, query: str) -> pd.DataFrame:
        """Runs a SQL query against the specified connection and returns a DataFrame."""
        session = self.get_connection(conn_id)
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        conn_type = registry[conn_id]["type"]
        
        if conn_type in ["sqlite", "postgres"]:
            return pd.read_sql_query(query, session)
        elif conn_type == "excel":
            # Simple simulation: query on Excel is not standard SQL, 
            # maybe pandas filtering or specific engine.
            return pd.read_excel(session)
        else:
            raise ValueError(f"Cannot run query on connection type '{conn_type}'")

if __name__ == "__main__":
    # Quick test with SQLite
    mgr = ConnectionManager("/tmp/test_connections.json")
    mgr.register_connection("test_db", "sqlite", {"path": ":memory:"})
    conn = mgr.get_connection("test_db")
    
    # Create test table
    conn.execute("CREATE TABLE users (id INT, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
    conn.commit()
    
    df = mgr.run_query("test_db", "SELECT * FROM users")
    print(df)
    
    os.remove("/tmp/test_connections.json")
