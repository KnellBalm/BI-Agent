# BI-Agent Phase 3a: 신규 연동 도구 설계 스펙

**날짜:** 2026-04-09  
**상태:** 승인됨  
**범위:** Redshift(IAM 인증), Airflow(DAG 관리), Metabase 강화 (+4개)

---

## 1. 목적

실무에서 사용하는 데이터 스택(Redshift, Airflow, Metabase)을 BI-Agent에 완전히 통합한다.

- Redshift: IAM 기반 임시 자격증명으로 보안 연결 + SQL 분석
- Airflow: 마트 파이프라인 상태 확인 및 수동 실행
- Metabase: Tableau 수준의 카드/대시보드 데이터 직접 조회

---

## 2. 아키텍처

기존 패턴 유지:
```
bi_agent_mcp/tools/{name}.py   ← 도구 구현
bi_agent_mcp/server.py         ← 등록
tests/unit/test_{name}.py      ← 단위 테스트
```

의존 패키지:
- Redshift: `boto3`, `psycopg2-binary`
- Airflow: `httpx` (이미 사용 중)
- Metabase: `httpx` (이미 사용 중)

---

## 3. Redshift 도구 (신규 4개)

파일: `bi_agent_mcp/tools/redshift.py`

### 인증 방식

boto3 `redshift.get_cluster_credentials()` → 임시 DB 비밀번호 발급 → psycopg2 연결

```
boto3.client('redshift', region_name=region)
.get_cluster_credentials(
    DbUser=user,
    DbName=database,
    ClusterIdentifier=cluster_id,
    DurationSeconds=3600,
    AutoCreate=False,
)
→ {"DbUser": "IAM:username", "DbPassword": "AmazonAWS..."}
```

Redshift 엔드포인트: `{cluster_id}.{region}.redshift.amazonaws.com:5439`

### 메모리 캐시

```python
_redshift_connections: Dict[str, dict] = {}
# {"conn_id": {"cluster_id": ..., "database": ..., "user": ..., "region": ...}}
```

### 도구 4개

#### 3-1. connect_redshift

```python
def connect_redshift(
    cluster_id: str,   # 예: "my-cluster" (not full endpoint)
    database: str,
    user: str,
    region: str = "ap-northeast-2",
    conn_id: str = "default",
) -> str:
    """[Redshift] AWS IAM 임시 자격증명으로 Redshift에 연결한다.
    
    boto3 환경(AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY 또는 IAM Role)이
    설정되어 있어야 한다.
    """
```

성공 시: `[OK] Redshift 연결 완료: {conn_id} ({cluster_id}/{database})`
실패 시: `[ERROR] Redshift 연결 실패: {e}`

#### 3-2. run_redshift_query

```python
def run_redshift_query(
    conn_id: str,
    sql: str,
    limit: int = 500,
) -> str:
    """[Redshift] Redshift에 SELECT 쿼리를 실행하고 결과를 반환한다."""
```

- `_validate_select(sql)` DML 차단 (기존 패턴)
- 결과: 마크다운 테이블 형식

#### 3-3. get_redshift_schema

```python
def get_redshift_schema(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift 스키마의 테이블 목록과 컬럼 정보를 반환한다."""
```

쿼리:
```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = '{schema}'
ORDER BY table_name, ordinal_position
```

#### 3-4. list_redshift_tables

```python
def list_redshift_tables(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift의 테이블 목록과 행 수를 반환한다."""
```

쿼리:
```sql
SELECT schemaname, tablename, tableowner
FROM pg_tables
WHERE schemaname = '{schema}'
ORDER BY tablename
```

---

## 4. Airflow 도구 (신규 6개)

파일: `bi_agent_mcp/tools/airflow.py`

### API 기반

Apache Airflow REST API v1 (`/api/v1`)  
인증: Basic Auth (username + password)  
공식 문서: https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html

### 메모리 캐시

```python
_airflow_connections: Dict[str, dict] = {}
# {"conn_id": {"base_url": "http://airflow:8080", "auth": ("user", "pass")}}
```

### 도구 6개

#### 4-1. connect_airflow

```python
def connect_airflow(
    base_url: str,   # 예: "http://airflow.internal:8080"
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Airflow] Airflow REST API에 연결한다."""
```

검증: `GET /api/v1/health` → `{"metadatabase": {"status": "healthy"}, "scheduler": {...}}`
성공 시: `[OK] Airflow 연결 완료: {conn_id} ({base_url})`

#### 4-2. list_airflow_dags

```python
def list_airflow_dags(
    conn_id: str,
    tags: str = None,       # 태그 필터 (쉼표 구분)
    only_active: bool = True,
    limit: int = 50,
) -> str:
    """[Airflow] DAG 목록과 마지막 실행 상태를 반환한다."""
```

`GET /api/v1/dags?limit={limit}&only_active={only_active}&tags={tags}`  
반환 필드: dag_id, is_active, is_paused, tags, last_parsed_time

#### 4-3. get_dag_status

```python
def get_dag_status(
    conn_id: str,
    dag_id: str,
) -> str:
    """[Airflow] DAG의 최근 실행 결과와 상태를 반환한다."""
```

`GET /api/v1/dags/{dag_id}/dagRuns?limit=5&order_by=-start_date`  
반환: dag_run_id, state(success/failed/running), start_date, end_date, duration

#### 4-4. trigger_dag

```python
def trigger_dag(
    conn_id: str,
    dag_id: str,
    conf: str = "{}",   # JSON 문자열로 전달
    logical_date: str = None,
) -> str:
    """[Airflow] DAG를 수동으로 트리거한다."""
```

`POST /api/v1/dags/{dag_id}/dagRuns`  
Body: `{"conf": {}, "logical_date": null}`  
성공 시: `[OK] DAG 트리거 완료: {dag_run_id} (state: queued)`

#### 4-5. get_task_logs

```python
def get_task_logs(
    conn_id: str,
    dag_id: str,
    dag_run_id: str,
    task_id: str,
    task_try_number: int = 1,
) -> str:
    """[Airflow] 특정 태스크의 실행 로그를 반환한다."""
```

`GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{task_try_number}`  
실패 원인 파악 및 마트 파이프라인 디버깅에 활용

#### 4-6. list_dag_runs

```python
def list_dag_runs(
    conn_id: str,
    dag_id: str,
    limit: int = 10,
) -> str:
    """[Airflow] DAG의 최근 실행 이력을 반환한다."""
```

`GET /api/v1/dags/{dag_id}/dagRuns?limit={limit}&order_by=-start_date`  
반환: 실행 일시, 상태, 소요 시간 목록

---

## 5. Metabase 강화 (기존 파일 수정, +4개)

파일: `bi_agent_mcp/tools/metabase.py` (수정)

기존 도구: connect_metabase, list_metabase_questions, run_metabase_question, list_metabase_dashboards

### 추가 도구 4개

#### 5-1. list_metabase_collections

```python
def list_metabase_collections(
    conn_id: str = "default",
) -> str:
    """[Metabase] 컬렉션(폴더) 목록과 구조를 반환한다."""
```

`GET /api/collection` — 전체 컬렉션 트리 반환  
반환: id, name, parent_id, 카드/대시보드 수

#### 5-2. get_metabase_card_data

```python
def get_metabase_card_data(
    conn_id: str,
    card_id: int,
    parameters: str = "[]",   # JSON 배열 문자열
) -> str:
    """[Metabase] 카드(질문)의 실제 데이터를 조회한다."""
```

`POST /api/card/{card_id}/query/json`  
Body: `{"parameters": []}`  
결과를 마크다운 테이블 형식으로 반환 (최대 500행)

이것이 Tableau `get_tableau_view_data`에 해당하는 기능.

#### 5-3. refresh_metabase_cache

```python
def refresh_metabase_cache(
    conn_id: str,
    card_id: int,
) -> str:
    """[Metabase] 카드의 캐시를 강제 새로고침한다."""
```

`POST /api/card/{card_id}/query`  
Body: `{"ignore_cache": true}`  
성공 시: `[OK] 카드 {card_id} 캐시 새로고침 완료`

#### 5-4. run_metabase_adhoc_sql

```python
def run_metabase_adhoc_sql(
    conn_id: str,
    database_id: int,
    sql: str,
    limit: int = 500,
) -> str:
    """[Metabase] Metabase에 연결된 데이터베이스에 Native SQL을 직접 실행한다."""
```

`POST /api/dataset`  
Body:
```json
{
  "database": database_id,
  "type": "native",
  "native": {"query": sql},
  "parameters": []
}
```
DML 차단 (`_validate_select` 적용)

---

## 6. 테스트 기준

```python
# redshift
test_connect_redshift_stores_connection()
test_connect_redshift_invalid_cluster_returns_error()
test_run_redshift_query_returns_results()
test_run_redshift_query_blocks_dml()
test_get_redshift_schema_returns_columns()
test_list_redshift_tables_returns_list()

# airflow
test_connect_airflow_stores_connection()
test_connect_airflow_health_check_failure_returns_error()
test_list_airflow_dags_returns_list()
test_get_dag_status_returns_runs()
test_trigger_dag_returns_run_id()
test_get_task_logs_returns_log_text()
test_list_dag_runs_returns_history()

# metabase (신규 4개)
test_list_metabase_collections_returns_tree()
test_get_metabase_card_data_returns_table()
test_refresh_metabase_cache_returns_ok()
test_run_metabase_adhoc_sql_returns_results()
test_run_metabase_adhoc_sql_blocks_dml()
```

모든 테스트는 `httpx.Client`를 mock으로 처리.

---

## 7. 파일 맵

| 파일 | 작업 | 신규 도구 수 |
|------|------|------|
| `bi_agent_mcp/tools/redshift.py` | 신규 | 4개 |
| `bi_agent_mcp/tools/airflow.py` | 신규 | 6개 |
| `bi_agent_mcp/tools/metabase.py` | 수정 | +4개 |
| `bi_agent_mcp/server.py` | 수정 | 14개 등록 |
| `tests/unit/test_redshift.py` | 신규 | |
| `tests/unit/test_airflow.py` | 신규 | |
| `tests/unit/test_metabase_enhanced.py` | 신규 | |

**총 14개 신규 도구** → 176 + 14 = **190개**

---

## 8. 제외 범위

- Redshift Serverless, Spectrum 외부 테이블 (Phase 3b)
- Airflow DAG 일시정지/재개 (trigger_dag로 충분)
- Metabase 알림/구독 관리
- Braze, DMS → Phase 3b
