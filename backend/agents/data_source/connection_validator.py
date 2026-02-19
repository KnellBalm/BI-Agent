"""
Connection Validator Module
Tests and validates database connections before registration.
"""

import time
import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
from backend.utils.logger_setup import setup_logger
from backend.utils.diagnostic_logger import diagnostic_logger

logger = setup_logger("connection_validator", "connection_validator.log")


@dataclass
class TestResult:
    """Result of a connection test"""
    success: bool
    latency_ms: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    suggestions: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        if self.success:
            return f"✓ Connection successful ({self.latency_ms:.0f}ms)"
        return f"✗ Connection failed: {self.error_message}\nSuggestions:\n" + "\n".join(f"  - {s}" for s in self.suggestions)


@dataclass
class ValidationResult:
    """Result of credential format validation"""
    valid: bool
    error_message: Optional[str] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        if self.valid:
            return "✓ Valid"
        return f"✗ {self.error_message}\nSuggestion: {self.suggestion}"


# Error pattern mapping for connection errors
ERROR_PATTERNS = {
    # PostgreSQL
    r"could not connect to server|Connection refused": "AUTH_FAILED",
    r"password authentication failed|FATAL.*password": "AUTH_FAILED",
    r"database.*does not exist": "DATABASE_NOT_FOUND",
    r"role.*does not exist": "USER_NOT_FOUND",
    r"SSL.*required": "SSL_REQUIRED",
    r"timeout|timed out": "NETWORK_TIMEOUT",
    r"Connection timed out": "NETWORK_TIMEOUT",
    r"No route to host": "HOST_UNREACHABLE",
    r"Name or service not known": "HOST_NOT_FOUND",

    # MySQL
    r"Access denied for user": "AUTH_FAILED",
    r"Unknown database": "DATABASE_NOT_FOUND",
    r"Can't connect to MySQL server": "HOST_UNREACHABLE",

    # General
    r"permission denied": "PERMISSION_DENIED",
    r"No such file or directory": "FILE_NOT_FOUND",
    r"Connection reset": "NETWORK_ERROR",
}


class ConnectionValidator:
    """Validates connections before registration"""

    @staticmethod
    def test_connection(conn_type: str, config: Dict[str, Any], ssh_config: Optional[Dict[str, Any]] = None) -> TestResult:
        """
        Test a connection using provided configuration.
        Supports SSH tunneling and various database types.
        """
        start_time = time.time()
        try:
            # Setup SSH tunnel if configured
            if ssh_config:
                ssh_result = ConnectionValidator._test_ssh_tunnel(ssh_config)
                if not ssh_result.success:
                    return ssh_result
                # Update config to use local tunnel
                config = config.copy()
                config['host'] = '127.0.0.1'
                config['port'] = ssh_result.metadata.get('local_port')

            # Test actual database connection
            if conn_type == "sqlite":
                result = ConnectionValidator._test_sqlite(config)
            elif conn_type == "postgres" or conn_type == "mysql":
                # Internalize SQLAlchemy URI construction
                from urllib.parse import quote_plus
                user = quote_plus(str(config.get('user', '')))
                password = quote_plus(str(config.get('password', '')))
                host = config.get('host', 'localhost')
                port = config.get('port', 5432 if conn_type == "postgres" else 3306)
                db = config.get('dbname') or config.get('database', '')
                dialect = "postgresql+psycopg2" if conn_type == "postgres" else "mysql+pymysql"
                
                uri = f"{dialect}://{user}:{password}@{host}:{port}/{db}"
                result = ConnectionValidator._test_sqlalchemy({"uri": uri})
            elif conn_type == "excel":
                result = ConnectionValidator._test_excel(config)
            elif conn_type == "duckdb":
                result = ConnectionValidator._test_duckdb(config)
            elif conn_type == "snowflake":
                result = ConnectionValidator._test_snowflake(config)
            elif conn_type == "bigquery":
                result = ConnectionValidator._test_bigquery(config)
            else:
                return TestResult(
                    success=False,
                    latency_ms=0,
                    error_code="UNSUPPORTED_TYPE",
                    error_message=f"Connection type '{conn_type}' is not supported",
                    suggestions=["Use one of: sqlite, postgres, mysql, excel, duckdb, snowflake, bigquery"]
                )

            # Calculate latency
            latency = (time.time() - start_time) * 1000
            result.latency_ms = latency

            if result.success:
                logger.info(f"{conn_type} connection test passed ({latency:.0f}ms)")
                diagnostic_logger.log_success("CONNECTION_TEST_PASSED", f"{conn_type} connection successful", {
                    "conn_type": conn_type,
                    "latency_ms": latency
                })
            else:
                logger.error(f"{conn_type} connection test failed: {result.error_message}")
                diagnostic_logger.log_error("CONNECTION_TEST_FAILED", result.error_message, {
                    "conn_type": conn_type,
                    "error_code": result.error_code,
                    "config": {k: v for k, v in config.items() if k != 'password'}
                })

            return result

        except Exception as e:
            logger.error(f"Connection test exception: {e}")
            try:
                diagnostic_logger.log_error("CONNECTION_TEST_EXCEPTION", str(e), {
                    "conn_type": conn_type,
                    "error": str(e)
                })
            except Exception:
                pass
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="EXCEPTION",
                error_message=str(e),
                suggestions=["Check if all required fields are provided", "Verify network connectivity"]
            )
    @staticmethod
    def _test_sqlalchemy(config: Dict[str, Any]) -> TestResult:
        """Test database connection using SQLAlchemy URI"""
        try:
            from sqlalchemy import create_engine
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="sqlalchemy is not installed",
                suggestions=["Install: pip install sqlalchemy"]
            )

        uri = config.get("uri")
        try:
            # We use a short timeout for the connection test
            connect_args = {"connect_timeout": 5}
            # Handle dialect-specific connect_args if needed
            if uri.startswith("postgresql"):
                pass
            elif uri.startswith("mysql"):
                pass
            
            engine = create_engine(uri, connect_args=connect_args if "sqlite" not in uri else {})
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )


    @staticmethod
    def _test_sqlite(config: Dict[str, Any]) -> TestResult:
        """Test SQLite connection"""
        import sqlite3
        import os

        path = config.get("path")
        if not path:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="CONFIG_ERROR",
                error_message="Path is required for SQLite",
                suggestions=["Provide 'path' in config"]
            )

        # Check if parent directory exists for new files
        if path != ":memory:" and not os.path.exists(path):
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                return TestResult(
                    success=False,
                    latency_ms=0,
                    error_code="PARENT_DIR_NOT_FOUND",
                    error_message=f"Parent directory does not exist: {parent_dir}",
                    suggestions=[f"Create directory: mkdir -p {parent_dir}"]
                )

        try:
            conn = sqlite3.connect(path)
            conn.execute("SELECT 1")
            conn.close()
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_postgres(config: Dict[str, Any]) -> TestResult:
        """Test PostgreSQL connection"""
        try:
            import psycopg2
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="psycopg2 is not installed",
                suggestions=["Install: pip install psycopg2-binary"]
            )

        try:
            conn = psycopg2.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5432),
                database=config.get('dbname') or config.get('database'),
                user=config.get('user'),
                password=config.get('password', ''),
                connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_mysql(config: Dict[str, Any]) -> TestResult:
        """Test MySQL connection"""
        try:
            import pymysql
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="pymysql is not installed",
                suggestions=["Install: pip install pymysql"]
            )

        try:
            conn = pymysql.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 3306),
                database=config.get('dbname') or config.get('database'),
                user=config.get('user'),
                password=config.get('password', ''),
                connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_excel(config: Dict[str, Any]) -> TestResult:
        """Test Excel file access"""
        import os

        path = config.get("path")
        if not path:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="CONFIG_ERROR",
                error_message="Path is required for Excel",
                suggestions=["Provide 'path' in config"]
            )

        if not os.path.exists(path):
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="FILE_NOT_FOUND",
                error_message=f"File not found: {path}",
                suggestions=[f"Check file exists: ls -la {path}"]
            )

        try:
            import pandas as pd
            df = pd.read_excel(path, nrows=1)
            return TestResult(success=True, latency_ms=0, metadata={"columns": len(df.columns)})
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="openpyxl is not installed",
                suggestions=["Install: pip install openpyxl"]
            )
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_duckdb(config: Dict[str, Any]) -> TestResult:
        """Test DuckDB connection"""
        try:
            import duckdb
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="duckdb is not installed",
                suggestions=["Install: pip install duckdb"]
            )

        try:
            path = config.get("path", ":memory:")
            conn = duckdb.connect(database=path)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_snowflake(config: Dict[str, Any]) -> TestResult:
        """Test Snowflake connection"""
        try:
            import snowflake.connector
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="snowflake-connector-python is not installed",
                suggestions=["Install: pip install snowflake-connector-python"]
            )

        try:
            conn = snowflake.connector.connect(
                account=config.get('account'),
                user=config.get('user'),
                password=config.get('password'),
                warehouse=config.get('warehouse'),
                database=config.get('database'),
                schema=config.get('schema')
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_bigquery(config: Dict[str, Any]) -> TestResult:
        """Test BigQuery connection"""
        try:
            from google.cloud import bigquery
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="google-cloud-bigquery is not installed",
                suggestions=["Install: pip install google-cloud-bigquery"]
            )

        try:
            credentials_file = config.get('credentials_file')
            if credentials_file:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file

            client = bigquery.Client(project=config.get('project_id'))
            query = "SELECT 1"
            query_job = client.query(query)
            list(query_job.result())
            return TestResult(success=True, latency_ms=0)
        except Exception as e:
            error_code = ConnectionValidator._classify_error(str(e))
            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=str(e),
                suggestions=suggest_connection_fix(error_code, str(e), config)
            )

    @staticmethod
    def _test_ssh_tunnel(ssh_config: Dict[str, Any]) -> TestResult:
        """Test SSH tunnel connection"""
        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError:
            return TestResult(
                success=False,
                latency_ms=0,
                error_code="LIBRARY_NOT_INSTALLED",
                error_message="sshtunnel is not installed",
                suggestions=["Install: pip install sshtunnel"]
            )

        try:
            ssh_kwargs = {
                'ssh_address_or_host': (ssh_config['host'], ssh_config.get('port', 22)),
                'ssh_username': ssh_config['username'],
                'remote_bind_address': (ssh_config.get('remote_host', '127.0.0.1'), ssh_config['remote_port']),
                'allow_agent': False,  # Avoid paramiko agent issues
                'host_pkey_directories': [],  # Avoid scanning for keys
            }

            if 'key_path' in ssh_config and ssh_config['key_path']:
                ssh_kwargs['ssh_pkey'] = ssh_config['key_path']
            elif 'password' in ssh_config and ssh_config['password']:
                ssh_kwargs['ssh_password'] = ssh_config['password']
            else:
                return TestResult(
                    success=False,
                    latency_ms=0,
                    error_code="SSH_AUTH_MISSING",
                    error_message="SSH 인증 정보가 필요합니다 (키 파일 또는 비밀번호)",
                    suggestions=["SSH 키 경로 또는 비밀번호를 입력해 주세요"]
                )

            tunnel = SSHTunnelForwarder(**ssh_kwargs)
            tunnel.start()
            local_port = tunnel.local_bind_port
            tunnel.stop()

            return TestResult(
                success=True,
                latency_ms=0,
                metadata={'local_port': local_port}
            )
        except Exception as e:
            error_msg = str(e)
            error_code = ConnectionValidator._classify_error(error_msg)
            
            suggestions = suggest_connection_fix(error_code, error_msg, ssh_config)
            
            # Specific check for Paramiko/DSSKey error
            if "DSSKey" in error_msg:
                error_code = "PARAMIKO_INCOMPATIBLE"
                suggestions.append("Paramiko 버전 호환성 문제일 수 있습니다. 'pip install paramiko==2.12.0'을 시도해 보세요.")

            return TestResult(
                success=False,
                latency_ms=0,
                error_code=error_code,
                error_message=error_msg,
                suggestions=suggestions
            )

    @staticmethod
    def _classify_error(error_msg: str) -> str:
        """Classify error message into error code"""
        for pattern, code in ERROR_PATTERNS.items():
            if re.search(pattern, error_msg, re.IGNORECASE):
                return code
        return "UNKNOWN_ERROR"

    @staticmethod
    def validate_credential_format(conn_type: str, credential_name: str, value: str) -> ValidationResult:
        """Validate credential format"""
        if credential_name == "port":
            try:
                port = int(value)
                if 1 <= port <= 65535:
                    return ValidationResult(valid=True)
                return ValidationResult(
                    valid=False,
                    error_message=f"Port {port} is out of range",
                    suggestion="Port must be between 1 and 65535"
                )
            except ValueError:
                return ValidationResult(
                    valid=False,
                    error_message=f"Invalid port: {value}",
                    suggestion="Port must be a number"
                )

        elif credential_name == "email" or credential_name == "user":
            if "@" in value and "." in value.split("@")[1]:
                return ValidationResult(valid=True)
            return ValidationResult(
                valid=False,
                error_message="Invalid email format",
                suggestion="Use format: user@domain.com"
            )

        elif credential_name == "host":
            if value.startswith("http://") or value.startswith("https://"):
                return ValidationResult(
                    valid=False,
                    error_message="Host should not include protocol",
                    suggestion=f"Use: {value.replace('https://', '').replace('http://', '')}"
                )
            return ValidationResult(valid=True)

        elif credential_name in ["path", "file_path", "credentials_file"]:
            if not value or value.strip() == "":
                return ValidationResult(
                    valid=False,
                    error_message="Path cannot be empty",
                    suggestion="Provide a valid file path"
                )
            return ValidationResult(valid=True)

        elif credential_name in ["database", "dbname"]:
            if not value or value.strip() == "":
                return ValidationResult(
                    valid=False,
                    error_message="Database name cannot be empty",
                    suggestion="Provide a valid database name"
                )
            return ValidationResult(valid=True)

        elif credential_name == "ssh_key_path":
            import os
            if os.path.exists(value):
                return ValidationResult(valid=True)
            return ValidationResult(
                valid=False,
                error_message=f"SSH key file not found: {value}",
                suggestion="Check the file path and ensure the key file exists"
            )

        return ValidationResult(valid=True)


def suggest_connection_fix(error_code: str, error_message: str, config: Dict[str, Any]) -> List[str]:
    """Suggest fixes based on error code"""
    suggestions = []

    if error_code == "AUTH_FAILED":
        suggestions.extend([
            "Verify username and password are correct",
            f"Check if user '{config.get('user')}' has permission to access the database",
            "Ensure the database account is not locked or expired"
        ])

    elif error_code == "NETWORK_TIMEOUT":
        suggestions.extend([
            f"Check if host '{config.get('host')}' is reachable: ping {config.get('host')}",
            f"Verify port {config.get('port')} is open: telnet {config.get('host')} {config.get('port')}",
            "Check firewall rules and network connectivity"
        ])

    elif error_code == "HOST_UNREACHABLE" or error_code == "HOST_NOT_FOUND":
        suggestions.extend([
            f"Verify hostname '{config.get('host')}' is correct",
            "Check DNS resolution: nslookup " + str(config.get('host')),
            "Try using IP address instead of hostname"
        ])

    elif error_code == "DATABASE_NOT_FOUND":
        suggestions.extend([
            f"Check if database '{config.get('dbname') or config.get('database')}' exists",
            "Verify database name spelling",
            "Create the database if it doesn't exist"
        ])

    elif error_code == "FILE_NOT_FOUND":
        path = config.get('path', '')
        suggestions.extend([
            f"Verify file exists: ls -la {path}",
            "Check file path spelling and permissions",
            f"Ensure you have read access to {path}"
        ])

    elif error_code == "PERMISSION_DENIED":
        suggestions.extend([
            "Check file/directory permissions",
            "Ensure your user account has necessary access rights",
            "Try running with appropriate permissions"
        ])

    elif error_code == "SSL_REQUIRED":
        suggestions.extend([
            "Add SSL configuration to connection",
            "Set ssl=True in config",
            "Provide SSL certificate if required"
        ])

    elif error_code == "SSH_AUTH_FAILED":
        suggestions.extend([
            "Verify SSH credentials (username/password or key file)",
            "Check SSH key file permissions (should be 600)",
            "Ensure SSH key is in correct format (PEM)"
        ])

    else:
        suggestions.append("Check the error message for specific details")

    return suggestions


# Convenience functions for backward compatibility
def test_connection(conn_type: str, config: Dict[str, Any], ssh_config: Optional[Dict[str, Any]] = None) -> TestResult:
    """Module-level convenience function"""
    return ConnectionValidator.test_connection(conn_type, config, ssh_config)


def validate_credential_format(conn_type: str, credential_name: str, value: str) -> ValidationResult:
    """Module-level convenience function"""
    return ConnectionValidator.validate_credential_format(conn_type, credential_name, value)
