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
from backend.utils.diagnostic_logger import diagnostic_logger
from backend.agents.data_source.connection_validator import test_connection

# Initialize localized logger
logger = setup_logger("connection_manager", "connections.log")

class ConnectionManager:
    """
    Manages connections to various data sources.
    Uses a local registry (connections.json) for persisting connection details.
    Supports SSH tunneling for remote database access.
    """
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.registry_path = path_manager.get_project_path(project_id) / "connections.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._active_connections = {}  # conn_id -> actual connection object
        self._ssh_tunnels = {}  # conn_id -> SSHTunnelForwarder instance
        logger.info(f"ConnectionManager initialized for project '{project_id}' at {self.registry_path}")
        
        # Auto-onboarding: Create sample if registry is empty
        self._auto_onboard_sample()

    def _auto_onboard_sample(self):
        """Checks if registry is empty and adds a sample SQLite source if needed."""
        try:
            # Ensure registry exists and is not empty
            if not os.path.exists(self.registry_path):
                registry = {}
            else:
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

    # _ensure_registry_exists method removed as its functionality is now handled in __init__ and _auto_onboard_sample

    def register_connection(self, conn_id: str, conn_type: str, config: Dict[str, Any], name: str = "", category: str = "DB"):
        """
        Registers a new connection in the local registry.
        Supports SSH tunneling via config['ssh'] = {host, port, username, key_path or password, remote_host, remote_port}
        """
        allowed_types = ["sqlite", "postgres", "mysql", "snowflake", "bigquery", "excel", "duckdb"]
        if conn_type not in allowed_types:
            logger.error(f"Unsupported connection type attempted: {conn_type}")
            raise ValueError(f"Unsupported connection type: {conn_type}. Valid types: {allowed_types}")

        # Basic Pre-flight check before registration
        self._validate_config(conn_type, config)

        # SSH 터널링 설정 확인 (테스트 전에 추출)
        ssh_config = config.get('ssh', None)

        # Test connection before registration - Apply env vars for testing
        logger.info(f"Testing connection before registering '{conn_id}'...")
        test_config = self._inject_env_vars(config.copy())
        test_ssh_config = self._inject_env_vars(ssh_config.copy()) if ssh_config else None
        test_result = test_connection(conn_type, test_config, test_ssh_config)

        if not test_result.success:
            error_msg = f"Connection test failed: {test_result.error_message}"
            suggestions_str = "\n".join(f"  - {s}" for s in test_result.suggestions)
            logger.error(f"{error_msg}\nSuggestions:\n{suggestions_str}")
            raise RuntimeError(f"{error_msg}\n\nSuggestions:\n{suggestions_str}")

        logger.info(f"Connection test passed ({test_result.latency_ms:.0f}ms)")

        try:
            if not os.path.exists(self.registry_path):
                registry = {}
            else:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)

            # SSH 터널링 설정을 config에서 제거하여 별도 관리
            ssh_config = config.pop('ssh', None)
            
            registry[conn_id] = {
                "type": conn_type,
                "name": name or conn_id,
                "category": category,
                "config": config,
                "ssh": ssh_config,  # SSH 설정 저장
                "created_at": datetime.datetime.now().isoformat(),
                "last_accessed": None
            }
            
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Connection '{conn_id}' registered successfully (type: {conn_type}, SSH: {bool(ssh_config)})")
            
            # SSH 터널이 필요한 경우 즉시 생성
            if ssh_config:
                self.close_ssh_tunnel(conn_id) # Close existing if updating
                self._start_ssh_tunnel(conn_id, ssh_config, config)
            return conn_id
        except Exception as e:
            logger.error(f"Failed to register connection {conn_id}: {e}")
            raise RuntimeError(f"Registration failed: {e}")

    def delete_connection(self, conn_id: str):
        """Removes a connection from registry and closes its resources."""
        try:
            if not os.path.exists(self.registry_path):
                return

            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            if conn_id in registry:
                # Close potential active resources
                self.close_ssh_tunnel(conn_id)
                if conn_id in self._active_connections: # Changed from self.active_sessions to self._active_connections
                    try:
                        session = self._active_connections.pop(conn_id) # Changed from self.active_sessions to self._active_connections
                        if hasattr(session, 'close'):
                            session.close()
                    except Exception as e:
                        logger.debug(f"Error closing session for {conn_id}: {e}")
                
                # Remove from registry
                del registry[conn_id]
                
                with open(self.registry_path, 'w', encoding='utf-8') as f:
                    json.dump(registry, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Connection '{conn_id}' deleted successfully.")
            else:
                logger.warning(f"Attempted to delete non-existent connection: {conn_id}")
        except Exception as e:
            logger.error(f"Failed to delete connection {conn_id}: {e}")
            raise RuntimeError(f"Deletion failed: {e}")

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
        if conn_id in self._active_connections:
            return self._active_connections[conn_id]

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            if conn_id not in registry:
                logger.error(f"Requested connection ID '{conn_id}' not found in registry.")
                raise ValueError(f"Connection ID '{conn_id}' is not registered.")
            
            conn_info = registry[conn_id]
            conn_type = conn_info["type"]
            config = self._inject_env_vars(conn_info["config"])
            
            # If SSH tunnel is configured, ensure it's started and update config
            if conn_info.get("ssh"):
                if conn_id not in self._ssh_tunnels:
                    self._start_ssh_tunnel(conn_id, conn_info["ssh"], config)
                
                # Update config to use the local tunnel port
                tunnel = self._ssh_tunnels[conn_id]
                config['host'] = '127.0.0.1'
                config['port'] = tunnel.local_bind_port
                logger.debug(f"Using SSH tunnel for {conn_id}: localhost:{tunnel.local_bind_port}")

            session = self._initialize_session(conn_type, config)
            self._active_connections[conn_id] = session

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
        """Initializes a connection session with error handling using SQLAlchemy internally."""
        try:
            from sqlalchemy import create_engine
            from urllib.parse import quote_plus
            
            if conn_type == "sqlite":
                path = config.get("path", ":memory:")
                # Use 3 slashes for absolute path, 4 for absolute path on some systems. 
                # sqlite:///path (relative) or sqlite:////path (absolute)
                # For simplicity, we'll prefix with sqlite:///
                prefix = "sqlite:///"
                if path != ":memory:" and not os.path.isabs(path):
                    logger.debug(f"Relative path for SQLite: {path}")
                return create_engine(f"{prefix}{path}")

            elif conn_type == "postgres" or conn_type == "mysql":
                user = quote_plus(str(config.get('user', '')))
                password = quote_plus(str(config.get('password', '')))
                host = config.get('host', 'localhost')
                port = config.get('port', 5432 if conn_type == "postgres" else 3306)
                db = config.get('dbname') or config.get('database', '')
                
                if conn_type == "postgres":
                    uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
                else:
                    uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
                
                return create_engine(uri)

            elif conn_type == "duckdb":
                path = config.get("path", ":memory:")
                return create_engine(f"duckdb:///{path}")

            elif conn_type == "excel":
                if not os.path.exists(config["path"]):
                    raise FileNotFoundError(f"Excel file not found: {config['path']}")
                return config["path"]

            else:
                raise NotImplementedError(f"Connection type '{conn_type}' is not supported yet.")
        except Exception as e:
            logger.error(f"Failed to initialize session for {conn_type}: {e}")
            safe_config = {k: v for k, v in config.items() if 'pass' not in k.lower()}
            diagnostic_logger.log_error("SESSION_INIT_FAILED", str(e), {"conn_type": conn_type, "config": safe_config})
            raise RuntimeError(f"Session initialization failed: {e}")

    def run_query(self, conn_id: str, query: str) -> pd.DataFrame:
        """Runs a SQL query with robust error handling and monitoring."""
        try:
            session = self.get_connection(conn_id)
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            conn_type = registry[conn_id]["type"]
            
            start_time = datetime.datetime.now()
            if conn_type in ["sqlite", "postgres", "mysql", "duckdb"]:
                # SQLAlchemy engines and duckdb work well with pd.read_sql
                # For SQLAlchemy 2.0+, we might need to use a connection or text()
                from sqlalchemy import text
                if hasattr(session, 'connect'): # It's likely an engine
                    with session.connect() as conn:
                        df = pd.read_sql_query(text(query), conn)
                else:
                    df = pd.read_sql_query(query, session)
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
            diagnostic_logger.log_error("QUERY_FAILED", str(e), {"conn_id": conn_id, "query": query})
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

    def _sanitize_table_name(self, name: str) -> str:
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if not sanitized[0].isalpha():
            sanitized = "t_" + sanitized
        return sanitized

    def _start_ssh_tunnel(self, conn_id: str, ssh_config: Dict[str, Any], db_config: Dict[str, Any]):
        """
        SSH 터널을 시작하고 로컬 포트로 포워딩합니다.
        ssh_config: {host, port, username, key_path or password, remote_host, remote_port}
        """
        try:
            from sshtunnel import SSHTunnelForwarder
            # diagnostic_logger is already imported at the top
            
            ssh_kwargs = {
                'ssh_address_or_host': (ssh_config['host'], ssh_config.get('port', 22)),
                'ssh_username': ssh_config['username'],
                'remote_bind_address': (ssh_config.get('remote_host', '127.0.0.1'), ssh_config['remote_port']),
                'allow_agent': False,  # Avoid paramiko 4.x DSSKey issue
                'host_pkey_directories': [],  # Avoid scanning for keys which triggers DSSKey
            }
            
            # 인증 방식: 키 파일 또는 비밀번호
            if 'key_path' in ssh_config and ssh_config['key_path']:
                ssh_kwargs['ssh_pkey'] = ssh_config['key_path']
            elif 'password' in ssh_config and ssh_config['password']:
                ssh_kwargs['ssh_password'] = ssh_config['password']
            else:
                raise ValueError("SSH 인증 정보가 필요합니다 (키 파일 또는 비밀번호)")
            
            tunnel = SSHTunnelForwarder(**ssh_kwargs)
            tunnel.start()
            
            self._ssh_tunnels[conn_id] = tunnel
            
            # DB config의 host와 port를 로컬 터널 포트로 변경 (이 변경은 db_config 객체에만 적용되며, registry에 저장된 config에는 영향을 주지 않음)
            # get_connection에서 이 정보를 사용하여 실제 연결을 수립할 때 적용됨.
            # db_config['host'] = '127.0.0.1' # This modification is not needed here, as get_connection will handle it.
            # db_config['port'] = tunnel.local_bind_port # Same here.
            
            logger.info(f"SSH tunnel started for '{conn_id}': localhost:{tunnel.local_bind_port} -> {ssh_config['host']}:{ssh_config.get('remote_host', '127.0.0.1')}:{ssh_config['remote_port']}")
            
        except Exception as e:
            logger.error(f"Failed to start SSH tunnel for '{conn_id}': {e}")
            safe_ssh = {k: v for k, v in ssh_config.items() if 'pass' not in k.lower()}
            diagnostic_logger.log_error("SSH_TUNNEL_START_FAILED", str(e), {"conn_id": conn_id, "ssh_config": safe_ssh})
            raise

    def close_ssh_tunnel(self, conn_id: str):
        """연결 ID에 대한 SSH 터널을 종료합니다."""
        if conn_id in self._ssh_tunnels:
            try:
                self._ssh_tunnels[conn_id].stop()
                del self._ssh_tunnels[conn_id]
                logger.info(f"SSH tunnel closed for '{conn_id}'")
            except Exception as e:
                logger.error(f"Error closing SSH tunnel for '{conn_id}': {e}")

    def close_all(self):
        """Cleanly closes all active sessions."""
        for conn_id, session in self._active_connections.items():
            try:
                if hasattr(session, 'close'):
                    session.close()
                logger.info(f"Closed session for {conn_id}")
            except Exception as e:
                logger.error(f"Error closing session for {conn_id}: {e}")
        self._active_connections.clear()
