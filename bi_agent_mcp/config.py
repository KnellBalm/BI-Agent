"""bi-agent 설정 및 환경변수 로드.

우선순위: 환경변수 → OS keyring (비밀 값에 한해 keyring fallback 지원)
"""
import os

from bi_agent_mcp.auth.credentials import get_env_or_secret

# 쿼리 결과 행 수 제한 (보안: 대량 데이터 노출 방지)
QUERY_LIMIT: int = int(os.environ.get("BI_AGENT_QUERY_LIMIT", "500"))

# PostgreSQL 기본값
PG_HOST: str = os.environ.get("BI_AGENT_PG_HOST", "localhost")
PG_PORT: int = int(os.environ.get("BI_AGENT_PG_PORT", "5432"))
PG_DBNAME: str = os.environ.get("BI_AGENT_PG_DBNAME", "")
PG_USER: str = os.environ.get("BI_AGENT_PG_USER", "")
PG_PASSWORD: str = get_env_or_secret("BI_AGENT_PG_PASSWORD", "bi-agent", "db_password") or ""

# MySQL 기본값
MYSQL_HOST: str = os.environ.get("BI_AGENT_MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.environ.get("BI_AGENT_MYSQL_PORT", "3306"))
MYSQL_DBNAME: str = os.environ.get("BI_AGENT_MYSQL_DBNAME", "")
MYSQL_USER: str = os.environ.get("BI_AGENT_MYSQL_USER", "")
MYSQL_PASSWORD: str = get_env_or_secret("BI_AGENT_MYSQL_PASSWORD", "bi-agent", "db_password") or ""

# Google OAuth
GOOGLE_CLIENT_ID: str = os.environ.get("BI_AGENT_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = get_env_or_secret("BI_AGENT_GOOGLE_CLIENT_SECRET", "bi-agent", "ga4_client_secret") or ""

# BigQuery
BQ_PROJECT_ID: str = os.getenv("BI_AGENT_BQ_PROJECT_ID", "")
BQ_DATASET: str = os.getenv("BI_AGENT_BQ_DATASET", "")
BQ_CREDENTIALS_PATH: str = os.getenv("BI_AGENT_BQ_CREDENTIALS_PATH", "")
BQ_MAX_BYTES_BILLED: int = int(os.getenv("BI_AGENT_BQ_MAX_BYTES_BILLED", "1000000000"))

# Amplitude
AMPLITUDE_API_KEY: str = get_env_or_secret("BI_AGENT_AMPLITUDE_API_KEY", "bi-agent", "amplitude_api_key") or ""
AMPLITUDE_SECRET_KEY: str = get_env_or_secret("BI_AGENT_AMPLITUDE_SECRET_KEY", "bi-agent", "amplitude_secret_key") or ""
