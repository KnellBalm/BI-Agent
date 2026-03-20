#!/usr/bin/env python3
"""
bi-agent MCP E2E 테스트 스크립트

실행 예시 (PostgreSQL):
    BI_AGENT_PG_HOST=localhost \
    BI_AGENT_PG_PORT=5432 \
    BI_AGENT_PG_DBNAME=testdb \
    BI_AGENT_PG_USER=postgres \
    BI_AGENT_PG_PASSWORD=secret \
    BI_E2E_DB_TYPE=postgresql \
    python tests/run_e2e.py

실행 예시 (MySQL):
    BI_AGENT_MYSQL_HOST=localhost \
    BI_AGENT_MYSQL_PORT=3306 \
    BI_AGENT_MYSQL_DBNAME=testdb \
    BI_AGENT_MYSQL_USER=root \
    BI_AGENT_MYSQL_PASSWORD=secret \
    BI_E2E_DB_TYPE=mysql \
    python tests/run_e2e.py

실행 예시 (BigQuery):
    BI_AGENT_BQ_PROJECT_ID=my-project \
    BI_AGENT_BQ_DATASET=my_dataset \
    BI_AGENT_BQ_CREDENTIALS_PATH=/path/to/sa.json \
    BI_E2E_TABLE=my_table \
    BI_E2E_DB_TYPE=bigquery \
    python tests/run_e2e.py
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bi_agent_mcp.tools.db import connect_db, list_connections, get_schema, run_query, profile_table


# ── 환경변수 읽기 ─────────────────────────────────────────────

DB_TYPE = os.environ.get("BI_E2E_DB_TYPE", "postgresql")
E2E_TABLE = os.environ.get("BI_E2E_TABLE", "")

PG_HOST = os.environ.get("BI_AGENT_PG_HOST", "localhost")
PG_PORT = int(os.environ.get("BI_AGENT_PG_PORT", "5432"))
PG_DBNAME = os.environ.get("BI_AGENT_PG_DBNAME", "")
PG_USER = os.environ.get("BI_AGENT_PG_USER", "")
PG_PASSWORD = os.environ.get("BI_AGENT_PG_PASSWORD", "")

MYSQL_HOST = os.environ.get("BI_AGENT_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("BI_AGENT_MYSQL_PORT", "3306"))
MYSQL_DBNAME = os.environ.get("BI_AGENT_MYSQL_DBNAME", "")
MYSQL_USER = os.environ.get("BI_AGENT_MYSQL_USER", "")
MYSQL_PASSWORD = os.environ.get("BI_AGENT_MYSQL_PASSWORD", "")

BQ_PROJECT_ID = os.environ.get("BI_AGENT_BQ_PROJECT_ID", "")
BQ_DATASET = os.environ.get("BI_AGENT_BQ_DATASET", "")


# ── 출력 헬퍼 ─────────────────────────────────────────────────

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_STEP = "[STEP]"


def step(name: str):
    print(f"\n{_STEP} {name}")
    print("-" * 60)


def check(label: str, result: str, expect_no_error: bool = True):
    has_error = "[ERROR]" in result
    ok = (not has_error) if expect_no_error else has_error
    status = _PASS if ok else _FAIL
    print(f"{status}  {label}")
    if not ok or os.environ.get("BI_E2E_VERBOSE"):
        # 실패 시 또는 VERBOSE 모드에서 결과 전체 출력
        for line in result.splitlines():
            print(f"       {line}")
    return ok


# ── 시나리오 ─────────────────────────────────────────────────

def run_postgresql_e2e():
    if not PG_DBNAME or not PG_USER:
        print("PostgreSQL 환경변수가 설정되지 않았습니다.")
        print("필요: BI_AGENT_PG_DBNAME, BI_AGENT_PG_USER, BI_AGENT_PG_PASSWORD")
        sys.exit(1)

    results = []

    # 1. connect_db
    step("1. connect_db (PostgreSQL)")
    result = connect_db(
        db_type="postgresql",
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DBNAME,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    print(result)
    results.append(check("connect_db 성공", result))

    if "[ERROR]" in result:
        print("\n연결 실패로 E2E 중단.")
        sys.exit(1)

    # conn_id 추출
    conn_id = result.split(":")[1].strip().split("\n")[0].strip()

    # 2. list_connections
    step("2. list_connections")
    result = list_connections()
    print(result)
    results.append(check("연결 목록 포함", result))
    results.append(check("비밀번호 마스킹 확인", result if "****" in result else "[ERROR] 마스킹 없음"))

    # 3. get_schema (테이블 목록)
    step("3. get_schema (테이블 목록)")
    result = get_schema(conn_id)
    print(result)
    results.append(check("스키마 목록 조회", result))

    # 4. get_schema (특정 테이블)
    table = E2E_TABLE
    if not table and "- " in result:
        # 결과에서 첫 번째 테이블명 자동 추출
        for line in result.splitlines():
            if line.startswith("- "):
                table = line[2:].split(" ")[0].strip()
                break

    if table:
        step(f"4. get_schema (테이블: {table})")
        result = get_schema(conn_id, table)
        print(result)
        results.append(check(f"테이블 '{table}' 컬럼 조회", result))

        # 5. run_query
        step(f"5. run_query (SELECT FROM {table})")
        result = run_query(conn_id, f"SELECT * FROM {table}")
        print(result)
        results.append(check("SELECT 쿼리 실행", result))

        # 6. run_query — 보안: DELETE 차단 확인
        step("6. run_query — DELETE 차단 확인")
        result = run_query(conn_id, f"DELETE FROM {table} WHERE 1=0")
        results.append(check("DELETE 차단됨", result, expect_no_error=False))
        print(f"       차단 메시지: {result}")

        # 7. profile_table
        step(f"7. profile_table (테이블: {table})")
        result = profile_table(conn_id, table)
        print(result)
        results.append(check("프로파일 통계 반환", result))
    else:
        print("테이블이 없어 4~7 단계를 건너뜁니다.")

    return results


def run_mysql_e2e():
    if not MYSQL_DBNAME or not MYSQL_USER:
        print("MySQL 환경변수가 설정되지 않았습니다.")
        print("필요: BI_AGENT_MYSQL_DBNAME, BI_AGENT_MYSQL_USER, BI_AGENT_MYSQL_PASSWORD")
        sys.exit(1)

    results = []

    step("1. connect_db (MySQL)")
    result = connect_db(
        db_type="mysql",
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DBNAME,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )
    print(result)
    results.append(check("connect_db 성공", result))

    if "[ERROR]" in result:
        print("\n연결 실패로 E2E 중단.")
        sys.exit(1)

    conn_id = result.split(":")[1].strip().split("\n")[0].strip()

    step("2. list_connections")
    result = list_connections()
    print(result)
    results.append(check("연결 목록 포함", result))

    step("3. get_schema (테이블 목록)")
    result = get_schema(conn_id)
    print(result)
    results.append(check("스키마 목록 조회", result))

    table = E2E_TABLE
    if not table and "- " in result:
        for line in result.splitlines():
            if line.startswith("- "):
                table = line[2:].strip()
                break

    if table:
        step(f"4. get_schema (테이블: {table})")
        result = get_schema(conn_id, table)
        print(result)
        results.append(check(f"테이블 '{table}' 컬럼 조회", result))

        step(f"5. run_query (SELECT FROM {table})")
        result = run_query(conn_id, f"SELECT * FROM {table}")
        print(result)
        results.append(check("SELECT 쿼리 실행", result))

        step("6. run_query — DROP 차단 확인")
        result = run_query(conn_id, f"DROP TABLE {table}")
        results.append(check("DROP 차단됨", result, expect_no_error=False))
        print(f"       차단 메시지: {result}")

        step(f"7. profile_table (테이블: {table})")
        result = profile_table(conn_id, table)
        print(result)
        results.append(check("프로파일 통계 반환", result))

    return results


def run_bigquery_e2e():
    if not BQ_PROJECT_ID or not BQ_DATASET:
        print("BigQuery 환경변수가 설정되지 않았습니다.")
        print("필요: BI_AGENT_BQ_PROJECT_ID, BI_AGENT_BQ_DATASET")
        sys.exit(1)

    results = []

    step("1. connect_db (BigQuery)")
    result = connect_db(
        db_type="bigquery",
        project_id=BQ_PROJECT_ID,
        dataset=BQ_DATASET,
    )
    print(result)
    results.append(check("connect_db 성공", result))

    if "[ERROR]" in result:
        print("\n연결 실패로 E2E 중단.")
        sys.exit(1)

    conn_id = result.split(":")[1].strip().split("\n")[0].strip()

    step("2. list_connections")
    result = list_connections()
    print(result)
    results.append(check("연결 목록 포함", result))

    step("3. get_schema (테이블 목록)")
    result = get_schema(conn_id)
    print(result)
    results.append(check("스키마 목록 조회", result))

    table = E2E_TABLE
    if not table and "- " in result:
        for line in result.splitlines():
            if line.startswith("- "):
                table = line[2:].strip()
                break

    if table:
        step(f"4. get_schema (테이블: {table})")
        result = get_schema(conn_id, table)
        print(result)
        results.append(check(f"테이블 '{table}' 컬럼 조회", result))

        step(f"5. run_query (SELECT FROM {table})")
        result = run_query(conn_id, f"SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{table}`")
        print(result)
        results.append(check("SELECT 쿼리 실행", result))

        step("6. run_query — DELETE 차단 확인")
        result = run_query(conn_id, f"DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{table}` WHERE TRUE")
        results.append(check("DELETE 차단됨", result, expect_no_error=False))
        print(f"       차단 메시지: {result}")

        step(f"7. profile_table (테이블: {table})")
        result = profile_table(conn_id, table)
        print(result)
        results.append(check("프로파일 통계 반환", result))

    return results


# ── 진입점 ────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"bi-agent MCP E2E 테스트  (DB: {DB_TYPE})")
    print("=" * 60)

    if DB_TYPE == "postgresql":
        results = run_postgresql_e2e()
    elif DB_TYPE == "mysql":
        results = run_mysql_e2e()
    elif DB_TYPE == "bigquery":
        results = run_bigquery_e2e()
    else:
        print(f"지원하지 않는 DB_TYPE: {DB_TYPE}")
        print("BI_E2E_DB_TYPE=postgresql|mysql|bigquery 를 설정하세요.")
        sys.exit(1)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"결과: {passed}/{total} 통과")
    if passed < total:
        print("일부 테스트 실패. 위 로그를 확인하세요.")
        sys.exit(1)
    else:
        print("모든 E2E 테스트 통과.")


if __name__ == "__main__":
    main()
