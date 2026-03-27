"""bi-agent 초기 설정 MCP 도구 — agent 대화 기반 setup."""

import logging

logger = logging.getLogger(__name__)

VALID_SOURCE_TYPES = ["postgresql", "mysql", "bigquery", "ga4", "amplitude"]


def check_setup_status() -> str:
    """[Setup] 현재 bi-agent 설정 상태를 확인합니다. 어떤 데이터 소스가 설정되어 있는지, 무엇이 필요한지 알려줍니다."""
    try:
        from bi_agent_mcp.config_manager import ConfigManager

        cm = ConfigManager()
        sources = cm.list_datasources()

        db = sources.get("db", {})
        ga4 = sources.get("ga4", {})
        amplitude = sources.get("amplitude", {})

        db_status = "✅ 설정됨"
        if db.get("configured"):
            db_type = db.get("type", "unknown")
            host = db.get("host", "")
            db_status = f"✅ 설정됨 ({db_type}{' - ' + host if host else ''})"
        else:
            db_status = "❌ 미설정"

        ga4_status = "✅ 설정됨" if ga4.get("configured") else "❌ 미설정"
        amplitude_status = "✅ 설정됨" if amplitude.get("configured") else "❌ 미설정"

        lines = [
            "📊 BI-Agent 설정 상태",
            "",
            f"데이터베이스: {db_status}",
            f"GA4:          {ga4_status}",
            f"Amplitude:    {amplitude_status}",
            "",
        ]

        missing = cm.get_missing_config()
        if missing:
            lines += [
                "💡 설정 방법 (configure_datasource 도구 사용):",
                "",
                "  # PostgreSQL 예시:",
                '  configure_datasource("postgresql", {"host": "localhost", "port": 5432, "database": "mydb", "user": "admin"}, {"password": "secret"})',
                "",
                "  # MySQL 예시:",
                '  configure_datasource("mysql", {"host": "localhost", "port": 3306, "database": "mydb", "user": "root"}, {"password": "secret"})',
                "",
                "  # BigQuery 예시:",
                '  configure_datasource("bigquery", {"project_id": "my-project", "dataset": "analytics"}, {})',
                "",
                "  # GA4 예시:",
                '  configure_datasource("ga4", {"property_id": "123456789"}, {"client_id": "xxx.apps.googleusercontent.com", "client_secret": "yyy"})',
                "",
                "  # Amplitude 예시:",
                '  configure_datasource("amplitude", {}, {"api_key": "xxx", "secret_key": "yyy"})',
            ]
        else:
            lines += ["✅ 모든 데이터 소스가 설정되어 있습니다!"]

        return "\n".join(lines)

    except Exception as e:
        logger.error("check_setup_status 실패: %s", e)
        return f"설정 상태 확인 중 오류 발생: {e}"


def configure_datasource(
    source_type: str, params: dict, secrets: dict | None = None
) -> str:
    """[Setup] 데이터 소스를 설정합니다. 비밀 값(패스워드, API 키)은 OS keyring에 안전하게 저장됩니다.

    Args:
        source_type: 데이터 소스 타입 ("postgresql", "mysql", "bigquery", "ga4", "amplitude")
        params: 비밀이 아닌 설정 값 (host, port, database, user, property_id 등)
        secrets: 비밀 값 (password, api_key, secret_key, client_id, client_secret 등)

    Returns:
        설정 결과 메시지
    """
    if source_type not in VALID_SOURCE_TYPES:
        return f"❌ 유효하지 않은 source_type: '{source_type}'. 가능한 값: {', '.join(VALID_SOURCE_TYPES)}"

    try:
        from bi_agent_mcp.config_manager import ConfigManager

        # DB 타입 정규화: postgresql/mysql/bigquery → db 카테고리로 저장
        config_key = source_type
        save_params = dict(params)

        if source_type in ("postgresql", "mysql", "bigquery"):
            config_key = "db"
            save_params["type"] = source_type

        cm = ConfigManager()
        cm.save_datasource(config_key, save_params, secrets)

        secret_count = len([v for v in (secrets or {}).values() if v])
        security_note = (
            f"\n🔐 {secret_count}개의 시크릿이 OS keyring에 안전하게 저장되었습니다 (설정 파일에 평문 없음)."
            if secret_count > 0
            else ""
        )

        return (
            f"✅ {source_type} 설정이 완료되었습니다.{security_note}\n"
            f"test_datasource(\"{source_type}\") 로 연결을 테스트할 수 있습니다."
        )

    except Exception as e:
        logger.error("configure_datasource 실패: source_type=%s, error=%s", source_type, e)
        return f"❌ {source_type} 설정 중 오류 발생: {e}"


def test_datasource(source_type: str) -> str:
    """[Setup]설정된 데이터 소스의 연결을 테스트합니다.

    Args:
        source_type: 테스트할 데이터 소스 타입

    Returns:
        테스트 결과 메시지
    """
    if source_type not in VALID_SOURCE_TYPES:
        return f"❌ 유효하지 않은 source_type: '{source_type}'. 가능한 값: {', '.join(VALID_SOURCE_TYPES)}"

    try:
        if source_type == "postgresql":
            return _test_postgresql()
        elif source_type == "mysql":
            return _test_mysql()
        elif source_type == "bigquery":
            return _test_bigquery()
        elif source_type == "ga4":
            return _test_ga4()
        elif source_type == "amplitude":
            return _test_amplitude()
        else:
            return f"❌ 알 수 없는 source_type: {source_type}"
    except Exception as e:
        logger.error("test_datasource 실패: source_type=%s, error=%s", source_type, e)
        return f"❌ {source_type} 연결 테스트 중 오류 발생: {e}"


def _test_postgresql() -> str:
    try:
        import psycopg2
        from bi_agent_mcp import config

        if not config.PG_HOST or not config.PG_DBNAME:
            from bi_agent_mcp.config_manager import ConfigManager
            cfg = ConfigManager().load_datasource("db")
            host = cfg.get("host", "localhost")
            port = int(cfg.get("port", 5432))
            dbname = cfg.get("database", cfg.get("dbname", ""))
            user = cfg.get("user", "")
            password = cfg.get("password", "")
        else:
            host = config.PG_HOST
            port = config.PG_PORT
            dbname = config.PG_DBNAME
            user = config.PG_USER
            password = config.PG_PASSWORD

        if not dbname:
            return "❌ PostgreSQL 설정이 없습니다. configure_datasource(\"postgresql\", ...) 로 먼저 설정해주세요."

        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=5)
        conn.close()
        return f"✅ PostgreSQL 연결 성공! ({user}@{host}:{port}/{dbname})"
    except ImportError:
        return "❌ psycopg2 미설치. pip install psycopg2-binary"
    except Exception as e:
        return f"❌ PostgreSQL 연결 실패: {e}"


def _test_mysql() -> str:
    try:
        import pymysql
        from bi_agent_mcp import config

        if not config.MYSQL_HOST or not config.MYSQL_DBNAME:
            from bi_agent_mcp.config_manager import ConfigManager
            cfg = ConfigManager().load_datasource("db")
            host = cfg.get("host", "localhost")
            port = int(cfg.get("port", 3306))
            dbname = cfg.get("database", cfg.get("dbname", ""))
            user = cfg.get("user", "")
            password = cfg.get("password", "")
        else:
            host = config.MYSQL_HOST
            port = config.MYSQL_PORT
            dbname = config.MYSQL_DBNAME
            user = config.MYSQL_USER
            password = config.MYSQL_PASSWORD

        if not dbname:
            return "❌ MySQL 설정이 없습니다. configure_datasource(\"mysql\", ...) 로 먼저 설정해주세요."

        conn = pymysql.connect(host=host, port=port, database=dbname, user=user, password=password, connect_timeout=5)
        conn.close()
        return f"✅ MySQL 연결 성공! ({user}@{host}:{port}/{dbname})"
    except ImportError:
        return "❌ pymysql 미설치. pip install pymysql"
    except Exception as e:
        return f"❌ MySQL 연결 실패: {e}"


def _test_bigquery() -> str:
    try:
        from google.cloud import bigquery
        from bi_agent_mcp import config

        project_id = config.BQ_PROJECT_ID
        if not project_id:
            from bi_agent_mcp.config_manager import ConfigManager
            cfg = ConfigManager().load_datasource("db")
            project_id = cfg.get("project_id", "")

        if not project_id:
            return "❌ BigQuery 설정이 없습니다. configure_datasource(\"bigquery\", ...) 로 먼저 설정해주세요."

        client = bigquery.Client(project=project_id)
        # 간단한 테스트 쿼리
        list(client.list_datasets(max_results=1))
        return f"✅ BigQuery 연결 성공! (project: {project_id})"
    except ImportError:
        return "❌ google-cloud-bigquery 미설치. pip install google-cloud-bigquery"
    except Exception as e:
        return f"❌ BigQuery 연결 실패: {e}"


def _test_ga4() -> str:
    from bi_agent_mcp import config
    from bi_agent_mcp.config_manager import ConfigManager

    client_id = config.GOOGLE_CLIENT_ID
    if not client_id:
        cfg = ConfigManager().load_datasource("ga4")
        client_id = cfg.get("client_id", "")

    if not client_id:
        return "❌ GA4 설정이 없습니다. configure_datasource(\"ga4\", ...) 로 먼저 설정해주세요."

    return f"✅ GA4 설정 확인됨 (Client ID 존재). 실제 데이터 조회는 connect_ga4() 를 사용하세요."


def _test_amplitude() -> str:
    from bi_agent_mcp import config

    if not config.AMPLITUDE_API_KEY:
        from bi_agent_mcp.config_manager import ConfigManager
        cfg = ConfigManager().load_datasource("amplitude")
        api_key = cfg.get("api_key", "")
    else:
        api_key = config.AMPLITUDE_API_KEY

    if not api_key:
        return "❌ Amplitude 설정이 없습니다. configure_datasource(\"amplitude\", ...) 로 먼저 설정해주세요."

    return "✅ Amplitude API 키 설정 확인됨. 실제 데이터 조회는 connect_amplitude() 를 사용하세요."
