# BI-Agent MCP 사용자 매뉴얼

## 목차
1. [개요](#개요)
2. [설치](#설치)
3. [빠른 시작 (5분)](#빠른-시작-5분)
4. [클라이언트 설정](#클라이언트-설정)
5. [데이터 소스 연결](#데이터-소스-연결)
6. [도구 레퍼런스](#도구-레퍼런스)
7. [실전 시나리오](#실전-시나리오)
8. [비즈니스 컨텍스트 설정](#비즈니스-컨텍스트-설정)
9. [보안](#보안)
10. [문제 해결](#문제-해결)

---

## 개요

**BI-Agent MCP**는 Claude, Cursor, VSCode Copilot, Antigravity 등 LLM 클라이언트에서 자연어로 데이터를 분석할 수 있는 MCP(Model Context Protocol) 서버입니다.

### 주요 기능

- **다중 DB 지원**: PostgreSQL, MySQL, BigQuery, Snowflake
- **파일 분석**: CSV/Excel을 로드하여 SQL로 직접 쿼리
- **외부 데이터**: Google Analytics 4, Amplitude 이벤트 조회
- **자동 분석**: 트렌드, 상관관계, 분포, 세그먼트, 퍼널, 코호트 분석
- **리포트 생성**: 마크다운 리포트, Tableau TWBX, Chart.js 대시보드(HTML)
- **데이터 품질**: 규칙 기반 검증(NULL 체크, 범위, 정규식, 유니크)
- **쿼리 관리**: 자주 쓰는 쿼리 저장/검색/실행
- **안전성**: 읽기 전용(SELECT만), 결과 행 제한, 자격증명 보호

### 도구 수

총 **38개 도구**:
- DB 도구 (5) + 파일 도구 (4) + 외부 데이터 (4) + 분석/리포트 (9) + 아웃풋 (3) + 품질/관리 (4) + 컨텍스트 (2) + 알림 (4) + 비교 (1) + 오케스트레이션 (8)

---

## 설치

### 요구사항

- Python 3.11 이상
- pip 또는 uv

### 방법 1: pip으로 설치 (권장)

```bash
pip install bi-agent-mcp
```

### 방법 2: 소스 설치 (개발)

```bash
git clone https://github.com/zokr/bi-agent.git
cd bi-agent
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# 또는
.venv\Scripts\activate             # Windows

pip install -e .
```

### 의존성 확인

```bash
python -c "import bi_agent_mcp; print('설치 성공')"
```

---

## 빠른 시작 (5분)

### 1단계: 설정 마법사 실행

```bash
bi-agent-mcp-setup
```

대화형 설치 마법사가 다음을 안내합니다:

1. **MCP 클라이언트 선택** (Claude Desktop, Cursor, VSCode 등)
2. **데이터베이스 설정** (PostgreSQL/MySQL/BigQuery)
3. **외부 데이터** (GA4, Amplitude)
4. **자격증명 저장** (OS 키체인에 안전 저장)

### 2단계: 클라이언트 재시작

설정한 클라이언트(Claude Desktop, Cursor 등)를 완전히 종료했다가 재시작합니다.

### 3단계: 첫 쿼리 실행

LLM 클라이언트에서:

```
"customers 테이블 스키마 보여줄래?"
```

또는

```
"최근 30일 일별 매출을 조회해줄래?"
```

---

## 클라이언트 설정

설정 마법사(`bi-agent-mcp-setup`)를 사용하는 것이 가장 간편합니다. 수동으로 설정하려면 아래를 참고하세요.

### Claude Desktop

**파일**: `~/.claude/claude_desktop_config.json` (macOS)
또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.example.com",
        "BI_AGENT_PG_PORT": "5432",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "bi_user",
        "BI_AGENT_PG_PASSWORD": "your_password"
      }
    }
  }
}
```

### Cursor

**파일**: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "postgres"
      }
    }
  }
}
```

### VSCode Copilot

**파일**: `.vscode/mcp.json` (프로젝트 폴더)

```json
{
  "servers": {
    "bi-agent": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
```

### Antigravity (Google Gemini)

**파일**: `~/.gemini/antigravity/mcp_config.json`

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
```

### Windsurf

**파일**: `.windsurf/mcp.json`

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
```

---

## 데이터 소스 연결

### PostgreSQL

#### 환경 변수

```bash
export BI_AGENT_PG_HOST=db.company.com
export BI_AGENT_PG_PORT=5432
export BI_AGENT_PG_DBNAME=analytics
export BI_AGENT_PG_USER=bi_user
export BI_AGENT_PG_PASSWORD=your_password
```

또는 `.env` 파일:

```
BI_AGENT_PG_HOST=localhost
BI_AGENT_PG_DBNAME=analytics
BI_AGENT_PG_USER=postgres
BI_AGENT_PG_PASSWORD=password
```

#### 연결 URL 형식

```
postgresql://user:password@host:5432/database
```

### MySQL

#### 환경 변수

```bash
export BI_AGENT_MYSQL_HOST=db.company.com
export BI_AGENT_MYSQL_PORT=3306
export BI_AGENT_MYSQL_DBNAME=analytics
export BI_AGENT_MYSQL_USER=bi_user
export BI_AGENT_MYSQL_PASSWORD=your_password
```

#### 연결 URL 형식

```
mysql://user:password@host:3306/database
```

### BigQuery

#### 환경 변수

```bash
export BI_AGENT_BQ_PROJECT_ID=my-gcp-project
export BI_AGENT_BQ_DATASET=analytics
export BI_AGENT_BQ_CREDENTIALS_PATH=/path/to/service-account-key.json
```

#### 서비스 계정 키 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 선택
2. 메뉴 > IAM 및 관리자 > 서비스 계정
3. 서비스 계정 생성 > BigQuery 데이터 편집자 역할 부여
4. 키 탭에서 JSON 키 생성 > 로컬에 저장

### Snowflake

#### 환경 변수

```bash
export BI_AGENT_SF_ACCOUNT=xy12345.us-east-1
export BI_AGENT_SF_USER=bi_user
export BI_AGENT_SF_PASSWORD=password
export BI_AGENT_SF_DATABASE=ANALYTICS
export BI_AGENT_SF_WAREHOUSE=COMPUTE_WH
```

### CSV/Excel 파일

파일은 CLI로 등록하거나 도구로 동적 로드:

```bash
# 파일 경로 지정
/path/to/data.csv
/path/to/sales.xlsx  (시트 지정 가능)
```

### Google Analytics 4

#### 환경 변수

```bash
export BI_AGENT_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
export BI_AGENT_GOOGLE_CLIENT_SECRET=your_secret
export BI_AGENT_GA4_PROPERTY_ID=123456789  # 선택
```

#### OAuth 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 OAuth 2.0 클라이언트 ID 생성
2. 애플리케이션 타입: "데스크톱 애플리케이션"
3. JSON 다운로드 > `client_id`, `client_secret` 환경 변수에 설정

### Amplitude

#### 환경 변수

```bash
export BI_AGENT_AMPLITUDE_API_KEY=your_api_key
export BI_AGENT_AMPLITUDE_SECRET_KEY=your_secret_key
```

#### API 키 생성

1. Amplitude 프로젝트 > 설정 > API 키 생성
2. 데이터 내보내기 권한 부여

---

## 도구 레퍼런스

### 데이터베이스 도구 (db.py)

#### `connect_db()`

데이터베이스 연결을 등록합니다.

```python
connect_db(
    db_type: str,          # "postgresql" | "mysql" | "bigquery" | "snowflake"
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    project_id: str = "",  # BigQuery 전용
    dataset: str = "",     # BigQuery 전용
    account: str = "",     # Snowflake 전용
    warehouse: str = ""    # Snowflake 전용
) -> str
```

**예시** (LLM 클라이언트):

```
"PostgreSQL 데이터베이스를 등록해줄래? 호스트는 localhost, 포트 5432, 데이터베이스는 analytics, 사용자는 postgres"
```

#### `list_connections()`

등록된 모든 연결을 조회합니다 (비밀번호 마스킹).

**예시**:

```
"어떤 데이터베이스를 등록했나?"
```

**응답**:

```
✓ conn_1 — postgresql (localhost:5432/analytics)
✓ conn_2 — bigquery (project: my-project, dataset: analytics)
```

#### `get_schema(conn_id, table_name="")`

테이블 스키마와 샘플 데이터를 조회합니다.

**예시**:

```
"customers 테이블 스키마 보여줄래?"
```

**응답**:

```
테이블: customers
컬럼:
  - customer_id (INTEGER) — PK
  - name (VARCHAR) — NOT NULL
  - email (VARCHAR)
  - created_at (TIMESTAMP)

샘플 데이터:
| customer_id | name | email |
|---|---|---|
| 1 | Alice | alice@example.com |
| 2 | Bob | bob@example.com |
```

#### `run_query(conn_id, sql)`

SELECT 쿼리를 실행합니다 (최대 500행, 읽기 전용).

**예시**:

```
"이 쿼리를 실행해줄래: SELECT * FROM orders LIMIT 10"
```

#### `profile_table(conn_id, table_name)`

테이블 프로파일링을 수행합니다 (NULL 비율, 유니크 값, 최댓값, 상위 5개).

**예시**:

```
"orders 테이블의 데이터 프로필을 생성해줄래"
```

---

### 파일 도구 (files.py)

#### `connect_file(path, sheet="")`

CSV 또는 Excel 파일을 로드합니다.

**예시**:

```
"/Users/alice/Downloads/sales_2024.csv 파일을 로드해줄래"
```

**응답**:

```
✓ file_id: abc123
  경로: /Users/alice/Downloads/sales_2024.csv
  행 수: 5,234
  컬럼: 15개
```

#### `list_files()`

로드된 모든 파일을 조회합니다.

**예시**:

```
"지금 로드된 파일 목록을 보여줄래"
```

#### `query_file(file_id, sql)`

파일 데이터에 SQL 쿼리를 실행합니다 (DuckDB 사용).

**예시**:

```
"sales_2024.csv에서 카테고리별 합계를 구해줄래"
```

**쿼리 (내부)**:

```sql
SELECT category, SUM(amount) as total
FROM file_abc123
GROUP BY category
```

---

### 분석/리포트 도구 (analysis.py)

#### `save_query(name, sql, connection_id="", tags=[], description="")`

자주 사용하는 SQL 쿼리를 저장합니다.

**예시**:

```
"이 쿼리를 '월별 매출'이라고 저장해줄래
SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as revenue
FROM orders
GROUP BY month
태그: ['매출', '월별']"
```

#### `list_saved_queries()`

저장된 쿼리 목록을 조회합니다.

**예시**:

```
"저장한 쿼리 목록을 보여줄래"
```

#### `search_saved_queries(keyword="", tags=[])`

쿼리를 키워드 또는 태그로 검색합니다.

**예시**:

```
"'매출' 관련 쿼리를 찾아줄래"
```

#### `run_saved_query(query_id, conn_id, params={})`

저장된 쿼리를 실행합니다.

**예시**:

```
"'월별 매출' 쿼리를 실행해줄래"
```

#### `delete_saved_query(query_id)`

저장된 쿼리를 삭제합니다.

#### `generate_report(sections)`

마크다운 리포트를 생성합니다.

**예시**:

```
마크다운 리포트 생성:
- 제목: "2024년 판매 분석"
- 섹션 1: "요약"
  내용: "지난 해 매출은 전년 대비 15% 증가했습니다."
- 섹션 2: "상위 고객"
  내용: "상위 5명 고객의 매출: ..."
```

**응답**:

```
✓ 리포트 생성됨: ~/Downloads/20240318_093000_bi_report.md
```

#### `load_domain_context(sections="all")`

비즈니스 도메인 컨텍스트를 로드합니다 (`context/` 디렉토리).

**예시**:

```
"도메인 컨텍스트를 로드해줄래"
```

---

### 외부 데이터 도구

#### GA4: `connect_ga4(property_id="")`

Google Analytics 4에 연결합니다 (OAuth).

#### GA4: `get_ga4_report(property_id, metric, dimensions, date_range)`

GA4 지표를 조회합니다.

**예시**:

```
"GA4에서 최근 30일 일별 방문자 수와 세션 수를 조회해줄래"
```

#### Amplitude: `connect_amplitude(api_key, secret_key)`

Amplitude에 연결합니다.

#### Amplitude: `get_amplitude_events(user_id, event, group_by, limit)`

Amplitude 이벤트를 조회합니다.

**예시**:

```
"Amplitude에서 사용자 12345의 최근 로그인 이벤트 10개를 보여줄래"
```

---

### BI 분석 도구 (analytics.py)

#### `trend_analysis(conn_id, sql, time_col, metric_cols, period="month")`

시계열 트렌드를 분석합니다 (기간별 집계 + 전기 대비 증감률).

**예시**:

```
"orders 테이블에서 매월 매출과 주문 수의 트렌드를 분석해줄래"
```

**내부 처리**:

```python
trend_analysis(
    conn_id="conn_1",
    sql="SELECT order_date, amount FROM orders",
    time_col="order_date",
    metric_cols=["amount"],
    period="month"
)
```

**응답**:

```
## 트렌드 분석 (month 단위)

| 기간 | amount | amount 증감률(%) |
|------|--------|-----------------|
| 2024-01 | 100,000.00 | — |
| 2024-02 | 112,000.00 | +12.0% |
| 2024-03 | 108,500.00 | -3.1% |
```

#### `correlation_analysis(conn_id, sql, columns=None)`

수치형 컬럼 간 Pearson 상관계수를 계산합니다.

**예시**:

```
"고객 테이블에서 나이, 구매 횟수, 평균 구매액 간의 상관관계를 분석해줄래"
```

**응답**:

```
## 상관계수 분석

|  | age | purchase_count | avg_amount |
|---|---|---|---|
| age | 1.00 | 0.62 | 0.55 |
| purchase_count | 0.62 | 1.00 | 0.89 |
| avg_amount | 0.55 | 0.89 | 1.00 |

주요 발견:
- 구매 횟수와 평균 구매액이 강한 양의 상관 (0.89)
```

#### `distribution_analysis(conn_id, sql, column, bins=10)`

컬럼의 분포를 히스토그램으로 분석합니다.

**예시**:

```
"고객의 나이 분포를 분석해줄래 (10개 구간)"
```

#### `segment_analysis(conn_id, sql, group_col, metric_col, agg="sum")`

세그먼트별 지표를 집계합니다.

**예시**:

```
"제품 카테고리별 매출과 수량을 분석해줄래"
```

**응답**:

```
## 세그먼트 분석

| category | sum(revenue) | sum(quantity) |
|---|---|---|
| Electronics | 580,000 | 1,200 |
| Clothing | 320,000 | 2,100 |
| Food | 180,000 | 5,500 |
```

#### `funnel_analysis(conn_id, steps)`

퍼널(단계별 전환율)을 분석합니다.

**예시**:

```
"회원가입 퍼널: 방문 → 가입 → 결제 → 재구매"
```

**내부 처리**:

```python
funnel_analysis(
    conn_id="conn_1",
    steps=[
        {"name": "방문", "sql": "SELECT COUNT(DISTINCT user_id) FROM page_views"},
        {"name": "가입", "sql": "SELECT COUNT(*) FROM users"},
        {"name": "결제", "sql": "SELECT COUNT(DISTINCT user_id) FROM orders"},
        {"name": "재구매", "sql": "SELECT COUNT(DISTINCT user_id) FROM orders WHERE purchase_count > 1"}
    ]
)
```

**응답**:

```
## 퍼널 분석

| 단계 | 수 | 전환율 |
|---|---|---|
| 방문 | 100,000 | 100% |
| 가입 | 25,000 | 25.0% |
| 결제 | 10,000 | 40.0% |
| 재구매 | 3,000 | 30.0% |
```

#### `cohort_analysis(conn_id, sql, user_col, cohort_date_col, activity_date_col)`

코호트별 리텐션을 분석합니다.

**예시**:

```
"2024년 월별 신규 고객의 재구매율 추이를 분석해줄래"
```

#### `pivot_table(conn_id, sql, index_col, columns_col, values_col, aggfunc="sum")`

피벗 테이블을 생성합니다.

**예시**:

```
"제품 카테고리 × 월별 매출 피벗 테이블을 만들어줄래"
```

#### `top_n_analysis(conn_id, sql, metric_col, n=10, group_col=None)`

상위 N개 항목을 분석합니다.

**예시**:

```
"상위 10개 제품을 매출 기준으로 보여줄래"
```

---

### 분석 오케스트레이션 도구 (orchestration.py)

LLM이 막연한 분석 요구를 구조화된 단계별 워크플로우로 관리합니다.

#### `create_analysis_plan(goal, context="", steps=None, tags=None)`

분석 계획을 생성합니다.

**예시**:

```
"2024년 판매 성과 분석이라는 주제로 분석 계획을 세워줄래"
```

**응답**:

```
✓ 분석 플랜 생성됨
  ID: plan_abc123
  상태: in_progress
  진행률: 0/5 단계
```

#### `get_analysis_plan(plan_id)`

분석 계획을 조회합니다.

#### `add_analysis_step(plan_id, title, description, tools_hint=[])`

분석 단계를 추가합니다.

**예시**:

```
"분석 플랜 plan_abc123에 '지역별 매출 비교' 단계를 추가해줄래.
권장 도구: segment_analysis, correlation_analysis"
```

#### `update_analysis_step(plan_id, step_idx, status, findings="")`

단계를 완료하고 발견사항을 기록합니다.

**예시**:

```
"단계 1을 완료했어. 발견사항: 아시아 지역이 전체 매출의 45%를 차지함"
```

#### `synthesize_findings(plan_id, format="summary")`

모든 단계의 발견사항을 종합합니다.

**예시**:

```
"분석 계획 plan_abc123의 결과를 최종 요약해줄래"
```

---

### 아웃풋 도구

#### `generate_dashboard(title, queries, output_path)`

Chart.js 기반 인터랙티브 대시보드(HTML)를 생성합니다.

**예시**:

```
"2024년 매출 대시보드를 생성해줄래
쿼리 1: SELECT DATE_TRUNC('month', order_date), SUM(amount) FROM orders GROUP BY 1
쿼리 2: SELECT category, SUM(amount) FROM orders GROUP BY 1
저장 위치: ~/Downloads/sales_dashboard.html"
```

**응답**:

```
✓ 대시보드 생성됨: ~/Downloads/sales_dashboard.html
  - 선 그래프: 월별 매출 추이
  - 원형 그래프: 카테고리별 매출 비율
```

#### `chart_from_file(file_id, title, x_col, y_col, chart_type)`

CSV/Excel 파일로 차트를 생성합니다.

**예시**:

```
"sales_2024.csv에서 '월별 매출 추이' 선 그래프를 생성해줄래
X축: month, Y축: revenue"
```

#### `generate_twbx(title, sql, conn_id, sheet_name, chart_type="auto")`

Tableau 워크북 (.twbx)을 생성합니다.

**예시**:

```
"orders 테이블의 매출 데이터로 Tableau 워크북을 만들어줄래"
```

---

### 데이터 품질 도구 (validation.py)

#### `validate_data(conn_id, table_name, rules)`

테이블에 데이터 품질 규칙을 적용합니다.

**예시**:

```
"orders 테이블 검증:
- order_date는 NULL이 아니어야 함
- amount는 0보다 커야 함
- status는 ['pending', 'completed', 'failed'] 중 하나여야 함"
```

**지원 규칙**:

| 규칙 | 설명 | 예시 |
|------|------|------|
| `not_null` | NULL 값 없음 | `{"col": "order_date", "rule": "not_null"}` |
| `range` | 값의 범위 | `{"col": "amount", "rule": "range", "min": 0, "max": 100000}` |
| `regex` | 정규식 매치 | `{"col": "email", "rule": "regex", "pattern": "^[\\w.-]+@[\\w.-]+\\.[a-z]{2,}$"}` |
| `enum` | 허용된 값 목록 | `{"col": "status", "rule": "enum", "values": ["pending", "completed"]}` |
| `unique` | 중복 없음 | `{"col": "order_id", "rule": "unique"}` |
| `freshness` | 최근 데이터 | `{"col": "created_at", "rule": "freshness", "max_age_days": 7}` |

**응답**:

```
## 데이터 검증 결과

테이블: orders

✓ order_date (NOT NULL): PASS (0 nulls found)
✓ amount (RANGE 0-100000): PASS (all values in range)
✗ status (ENUM): FAIL (2 invalid values found: 'unknown')

전체: 3/4 규칙 통과 (75%)
```

#### `validate_query_result(conn_id, sql, rules)`

쿼리 결과에 검증을 적용합니다.

---

### 비교 도구 (compare.py)

#### `compare_queries(conn_id, sql_a, sql_b, key_columns=[])`

두 쿼리 결과를 비교합니다.

**예시**:

```
"지난달 매출과 이번달 매출을 비교해줄래
쿼리 A: SELECT * FROM monthly_sales WHERE month = '2024-02'
쿼리 B: SELECT * FROM monthly_sales WHERE month = '2024-03'
비교 키: category"
```

**응답**:

```
## 쿼리 비교 분석

추가된 행 (B에만 있음): 2개
삭제된 행 (A에만 있음): 1개
변경된 행: 5개

주요 변화:
- electronics: 100,000 → 112,000 (+12.0%)
- clothing: 80,000 → 75,000 (-6.3%)
```

---

### 컨텍스트 도구 (context.py)

#### `get_context_for_question(conn_id, question)`

자연어 질문에 관련된 테이블과 컬럼을 추천합니다.

**예시**:

```
"지난 30일 일별 매출 트렌드"를 분석하려면 어떤 테이블을 사용해야 할까?"
```

**응답**:

```
## 권장 테이블

1. orders (신뢰도: 95%)
   - order_id (INTEGER, PK)
   - order_date (DATE) ← 날짜 필터 추천
   - amount (DECIMAL) ← 매출 집계 추천
   - status (VARCHAR)

2. transactions (신뢰도: 80%)
   - transaction_date (TIMESTAMP)
   - revenue (DECIMAL)

권장 SQL:
SELECT DATE(order_date) as date, SUM(amount) as revenue
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
```

#### `get_table_relationships(conn_id)`

테이블 간 관계(외래키 등)를 조회합니다.

**예시**:

```
"테이블 관계도를 보여줄래"
```

---

### 알림 도구 (alerts.py)

#### `create_alert(conn_id, name, sql, condition, message="")`

SQL 기반 알림을 등록합니다.

**예시**:

```
"이름: '일일 매출 하락 알림'
조건: SELECT SUM(amount) FROM orders WHERE order_date = CURRENT_DATE
평가: < 50000 (매출이 5만 미만이면 알림)
메시지: '주의! 오늘 매출이 목표치 이하입니다.'"
```

**지원 조건**:

| 조건 | 설명 | 예시 |
|------|------|------|
| `gt` | 초과 | `gt:10000` |
| `gte` | 이상 | `gte:5000` |
| `lt` | 미만 | `lt:50000` |
| `lte` | 이하 | `lte:5000` |
| `eq` | 같음 | `eq:0` |
| `ne` | 다름 | `ne:pending` |

#### `check_alerts(alert_id="")`

알림 조건을 평가합니다.

**예시**:

```
"모든 알림을 확인해줄래"
```

**응답**:

```
## 알림 상태

✓ 일일 매출 하락 알림: OK (매출: 75,000)
✗ 고객 이탈 알림: TRIGGERED (이탈자: 5명, 임계값: 3명)
```

#### `list_alerts()`

등록된 모든 알림을 조회합니다.

#### `delete_alert(alert_id)`

알림을 삭제합니다.

---

### 설정 도구 (setup.py)

#### `check_setup_status()`

현재 설정 상태를 확인합니다.

**예시**:

```
"설정 상태를 확인해줄래"
```

**응답**:

```
## 설정 상태

📊 데이터베이스
  ✓ PostgreSQL: conn_1 (localhost:5432/analytics)
  ✗ BigQuery: 미설정

📈 외부 데이터
  ✓ Google Analytics 4: property_id = 123456
  ✗ Amplitude: 미설정

💾 파일
  ✓ 로드된 파일: 2개 (sales_2024.csv, customers.xlsx)
```

#### `configure_datasource(source_type, config, sensitive={})`

데이터 소스 자격증명을 등록합니다.

#### `test_datasource(source_type)`

연결을 테스트합니다.

---

## 실전 시나리오

### 시나리오 1: 월별 매출 분석

```
"지난 12개월 월별 매출과 전기 대비 증감률을 보여줄래"
```

**LLM의 내부 처리**:

1. 테이블 추천 → `get_context_for_question`
2. 데이터 조회 → `run_query` ("SELECT DATE_TRUNC('month', order_date), SUM(amount) FROM orders GROUP BY 1")
3. 트렌드 분석 → `trend_analysis` (period="month")
4. 리포트 생성 → `generate_report` (트렌드 테이블 + 분석 의견)

---

### 시나리오 2: 고객 세그먼트 분석

```
"고객을 연령대별로 분석해줄래. 각 세그먼트의 평균 구매액과 구매 횟수를 보고 싶어"
```

**LLM의 내부 처리**:

1. 스키마 조회 → `get_schema` (customers)
2. 세그먼트 분석 → `segment_analysis` (group_col="age_group", metric_col=["avg_amount", "purchase_count"])
3. 상관관계 분석 → `correlation_analysis` (연령과 구매액 상관성)
4. 리포트 생성 → `generate_report`

---

### 시나리오 3: 퍼널 분석 (전환율)

```
"사용자 가입부터 결제까지의 전환율을 보여줄래"
```

**LLM의 내부 처리**:

1. 각 단계별 쿼리 작성 (방문 → 가입 → 결제)
2. `funnel_analysis` 실행
3. 각 단계의 드롭 원인 분석
4. 마크다운 리포트 생성

---

### 시나리오 4: 데이터 품질 검증

```
"orders 테이블의 데이터 품질을 검증해줄래. order_id는 중복 없고, amount는 0보다 커야 하며, status는 valid 값만 있어야 해"
```

**LLM의 내부 처리**:

1. `validate_data` 실행 (not_null, unique, range, enum 규칙)
2. 위반 사항 조회
3. 문제 데이터 샘플 표시
4. 정정 SQL 제안

---

### 시나리오 5: 두 기간 비교

```
"작년 같은 기간과 올해를 비교해줄래. 제품별 매출 추이를 보고 싶어"
```

**LLM의 내부 처리**:

1. 작년 쿼리: `SELECT category, SUM(amount) FROM orders WHERE year(order_date) = 2023 GROUP BY 1`
2. 올해 쿼리: `SELECT category, SUM(amount) FROM orders WHERE year(order_date) = 2024 GROUP BY 1`
3. `compare_queries` (key_columns=["category"])
4. 각 카테고리별 성장률 표시

---

### 시나리오 6: 다중 소스 분석

```
"GA4의 방문자 데이터와 우리 주문 데이터를 비교해줄래"
```

**LLM의 내부 처리**:

1. GA4에서 일별 방문자 조회 → `get_ga4_report`
2. DB에서 일별 주문 수 조회 → `run_query`
3. 두 데이터를 연결 (날짜 기준) → `cross_query`
4. 상관관계 분석 → 방문 증가 → 주문 증가?

---

## 비즈니스 컨텍스트 설정

LLM이 더 정확한 분석 방향을 제안하도록 비즈니스 도메인 지식을 등록할 수 있습니다.

### context/ 디렉토리 구조

```
~/.bi-agent-mcp/context/
├── business.md          # 회사 및 비즈니스 개요
├── metrics.md           # KPI, 지표 정의
├── glossary.md          # 용어 사전
├── rules.md             # 비즈니스 규칙
└── recent_events.md     # 최근 중요 이벤트
```

### business.md 예시

```markdown
# 비즈니스 개요

## 회사
- 이름: ABC 전자상거래
- 산업: 온라인 소매
- 주력 제품: 전자제품, 의류, 식품

## 비즈니스 모델
- B2C 직판
- 2024년 목표 매출: 100억원
- 주요 마케팅 채널: Google, Facebook, Email
```

### metrics.md 예시

```markdown
# KPI 및 지표

## 매출 지표
- **GMV (상품 거래액)**: 주문 × 평균 주문액
- **매출 (Revenue)**: GMV - 환불액 - 할인
- **월별 성장률**: (이번달 - 지난달) / 지난달 × 100%
- **카테고리 집중도**: 상위 3개 카테고리 매출 비중

## 고객 지표
- **신규 고객**: 첫 구매 고객
- **기존 고객**: 2회 이상 구매
- **이탈**: 30일 이상 구매 없음
- **LTV (생애가치)**: 고객당 누적 매출
```

### glossary.md 예시

```markdown
# 용어 사전

| 용어 | 설명 |
|------|------|
| SKU | 상품 코드 (product_id) |
| CSR | 고객 반품률 (refund / order 비율) |
| AOV | 평균 주문액 (revenue / order 수) |
| CAC | 고객 획득 비용 (마케팅비 / 신규 고객) |
```

### rules.md 예시

```markdown
# 비즈니스 규칙

- 무료배송 임계값: 3만원 이상
- 환불 기간: 구매 후 7일 이내
- 적립금 환산율: 1% (1만원 구매 = 100포인트)
- VIP 기준: 월 구매액 50만원 이상
```

### context 로드

LLM에게 다음과 같이 요청:

```
"비즈니스 컨텍스트를 로드해줄래"
```

이후 LLM은:

```
지난 분기 매출이 목표의 80%에 불과하네요.
주요 원인 분석:
1. 신규 고객 유입 부족 (CAC 상승으로 마케팅 효율 악화)
2. 기존 고객 이탈 증가 (LTV 하락)
3. 상품 집중도 증가 (상위 3개 카테고리 비중 75% → 82%)

권장 액션:
- 마케팅 효율 개선 필요
- 고객 리텐션 프로그램 강화
- 신규 카테고리 상품 강화
```

---

## 보안

### 핵심 원칙

1. **SELECT 전용**: INSERT, UPDATE, DELETE, DROP 등 쓰기 쿼리 자동 차단
2. **결과 행 제한**: 기본 500행 (환경 변수로 조정 가능)
3. **로컬 처리**: 모든 데이터는 사용자 로컬 또는 사내 네트워크에서만 처리
4. **자격증명 보호**: 평문 로그 없음, 민감한 정보 마스킹

### 자격증명 저장

#### 환경 변수 (권장)

```bash
# .env 파일 (`.gitignore`에 포함)
BI_AGENT_PG_PASSWORD=your_password
BI_AGENT_BQ_CREDENTIALS_PATH=/path/to/key.json
```

#### OS 키체인 (권장)

설정 마법사 실행 시 자동으로 OS 키체인에 저장:

```bash
bi-agent-mcp-setup
```

- **macOS**: Keychain
- **Linux**: libsecret
- **Windows**: Credential Manager

#### 설정 파일

절대 설정 파일에 비밀번호를 저장하지 마세요.

```json
// ❌ 나쁜 예
{
  "mcpServers": {
    "bi-agent": {
      "env": {
        "BI_AGENT_PG_PASSWORD": "your_password"  // 위험!
      }
    }
  }
}

// ✅ 좋은 예
{
  "mcpServers": {
    "bi-agent": {
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
// 비밀번호는 환경 변수 또는 OS 키체인에서 읽음
```

### 데이터 개인정보보호

- 쿼리 결과는 로컬 메모리에서만 처리
- LLM API로 전송되는 것은 텍스트 표현만 (원본 데이터 아님)
- 저장된 쿼리는 SQL만 저장 (결과 데이터 제외)
- 로그에 민감한 데이터 없음

---

## 문제 해결

### Q: "연결할 수 없습니다" 오류가 나요

**A: 다음을 확인하세요:**

1. 환경 변수 설정 확인:
   ```bash
   echo $BI_AGENT_PG_HOST
   ```

2. 데이터베이스 연결성 테스트:
   ```bash
   psql -h $BI_AGENT_PG_HOST -U $BI_AGENT_PG_USER -d $BI_AGENT_PG_DBNAME
   ```

3. 클라이언트 재시작

4. `check_setup_status` 도구 실행:
   ```
   "설정 상태를 확인해줄래"
   ```

---

### Q: 쿼리 실행이 너무 느려요

**A:**

1. 행 제한 확인:
   ```bash
   export BI_AGENT_QUERY_LIMIT=1000  # 기본값: 500
   ```

2. 인덱스 확인 (DB 관리자):
   ```sql
   -- PostgreSQL
   CREATE INDEX idx_orders_order_date ON orders(order_date);
   ```

3. 데이터 프로파일링 대신 샘플 조회:
   ```
   "orders 테이블의 처음 100행만 보여줄래"
   ```

---

### Q: 특정 테이블에 액세스할 수 없어요

**A:**

1. DB 권한 확인:
   ```sql
   -- PostgreSQL
   GRANT SELECT ON all tables in schema public TO bi_user;
   ```

2. 스키마 조회:
   ```
   "어떤 테이블들이 있는지 보여줄래?"
   ```

3. 특정 테이블 스키마:
   ```
   "customers 테이블이 존재하는지 확인해줄래"
   ```

---

### Q: 대시보드 생성이 실패했어요

**A:**

1. 출력 경로 확인:
   ```bash
   # 디렉토리 생성
   mkdir -p ~/Downloads
   ```

2. 쿼리 검증 (SELECT만 포함?):
   ```
   "이 쿼리를 실행해봐줄래: SELECT * FROM orders LIMIT 5"
   ```

3. 파일 권한:
   ```bash
   chmod 755 ~/Downloads
   ```

---

### Q: GA4 또는 Amplitude 연결이 안 되요

**A:**

1. API 키 확인:
   ```bash
   echo $BI_AGENT_AMPLITUDE_API_KEY
   ```

2. 권한 확인 (각 서비스 콘솔):
   - GA4: 보기 권한 필요
   - Amplitude: 데이터 내보내기 권한 필요

3. 테스트:
   ```
   "Amplitude 연결을 테스트해줄래"
   ```

---

### Q: 저장된 쿼리를 찾을 수 없어요

**A:**

1. 저장 위치 확인:
   ```bash
   cat ~/.bi-agent-mcp/saved_queries.json
   ```

2. 쿼리 검색:
   ```
   "저장된 쿼리 중에 '매출' 관련된 것들을 보여줄래"
   ```

3. 쿼리 목록:
   ```
   "모든 저장된 쿼리를 보여줄래"
   ```

---

### Q: 오케스트레이션 플랜이 꼬였어요

**A:**

1. 플랜 목록:
   ```
   "진행 중인 분석 플랜을 모두 보여줄래"
   ```

2. 플랜 상태 확인:
   ```
   "플랜 plan_abc123의 현재 진행 상황을 보여줄래"
   ```

3. 플랜 취소:
   ```
   "플랜 plan_abc123을 완료 처리해줄래"
   ```

4. 수동 삭제:
   ```bash
   rm ~/.bi-agent-mcp/analysis_plans/plan_abc123.json
   ```

---

### Q: Python 버전 호환성 문제

**A:**

```bash
python --version          # 3.11 이상 필수
python -m pip --version   # pip 최신 버전

# 가상환경 재생성
python -m venv .venv --upgrade-deps
source .venv/bin/activate
pip install bi-agent-mcp
```

---

### Q: 도구를 찾을 수 없습니다

**A:**

1. MCP 서버 상태 확인 (클라이언트 로그):
   ```
   "사용 가능한 도구들을 보여줄래"
   ```

2. 클라이언트 재시작:
   - Claude Desktop: 완전히 종료 후 재시작
   - Cursor: 재시작
   - VSCode: 창 재로드 (Cmd/Ctrl+Shift+P > Reload Window)

3. 설정 파일 검증:
   ```bash
   # Claude Desktop
   cat ~/.claude/claude_desktop_config.json | python -m json.tool
   ```

---

## 문의 및 피드백

문제가 발생하면:

1. [공식 문서](../DESIGN.md)를 확인
2. GitHub Issues에서 유사한 이슈 검색
3. 새로운 이슈 생성 시 다음 정보 포함:
   - Python 버전 (`python --version`)
   - 설치 방식 (pip vs git clone)
   - 클라이언트 (Claude Desktop, Cursor 등)
   - 오류 메시지
   - 재현 단계

---

## 라이센스

MIT License

## 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다!

---

마지막 업데이트: 2026-03-25
