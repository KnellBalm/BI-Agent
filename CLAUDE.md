# BI-Agent MCP — 프로젝트 가이드

## 프로젝트 개요

BI 분석가를 위한 MCP(Model Context Protocol) 서버. Claude Desktop, Cursor, VSCode 등 MCP 클라이언트에서 자연어로 데이터를 분석한다.

- **진입점**: `bi_agent_mcp/server.py` — FastMCP 인스턴스, 전체 도구 등록
- **총 도구 수**: 171개 (2026-04 기준)
- **테스트**: `tests/unit/` — 834+ 단위 테스트, 커버리지 게이트 80%

---

## 아키텍처

```
bi_agent_mcp/
├── server.py          # FastMCP 등록 허브 (모든 도구 import/등록)
├── config.py          # QUERY_LIMIT 등 환경 설정
└── tools/
    ├── db.py           # _connections, _get_conn, _validate_select (공유 헬퍼)
    ├── files.py        # _files (파일 소스 상태)
    ├── analytics.py    # [Analytics] 8개
    ├── business.py     # [Business] 6개
    ├── product.py      # [Product] 5개
    ├── marketing.py    # [Marketing] 4개
    ├── forecast.py     # [Forecast] 3개
    ├── anomaly.py      # [Anomaly] 2개
    ├── stats.py        # [Stats] 11개 (기술통계/추론통계/가설검정)
    ├── ab_test.py      # [ABTest] 4개 (전문 A/B 분석)
    ├── helper.py       # [Helper] 4개 (가설검증/방법론/결과해석/Tableau)
    ├── viz_helper.py   # [Helper] 2개 (시각화 어드바이저/대시보드 설계)
    ├── bi_helper.py    # [Helper] 1개 (도구 선택기)
    ├── validation.py   # [Quality] 2개
    ├── compare.py      # [Compare] 1개
    ├── cross_source.py # [CrossSource] 1개
    ├── alerts.py       # [Alert] 4개
    ├── orchestration.py# [Orchestration] 8개
    ├── dashboard.py    # [Dashboard] 2개
    ├── tableau.py      # [Export] 1개
    ├── text_to_sql.py  # 1개
    ├── analysis.py     # 9개
    ├── context.py      # 2개
    ├── setup.py        # 3개
    ├── ga4.py          # 2개
    ├── amplitude.py    # 2개
    ├── redash.py       # [Redash] 4개
    ├── grafana.py      # [Grafana] 4개
    ├── segment.py      # [Segment] 4개
    └── dbt_cloud.py    # [dbtCloud] 4개
```

---

## 도구 카테고리 (157개)

| 카테고리 | 파일 | 개수 | 태그 |
|---------|------|------|------|
| DB 연결/쿼리 | db.py + files.py | 10 | — |
| 외부 소스 | ga4.py + amplitude.py | 4 | — |
| 분석/리포트 | analysis.py | 9 | — |
| 아웃풋 | dashboard.py, tableau.py | 4 | [Dashboard][Export] |
| BI 심층 분석 | analytics.py | 8 | [Analytics] |
| 오케스트레이션 | orchestration.py | 8 | [Orchestration] |
| 비즈니스 | business.py | 6 | [Business] |
| 프로덕트 | product.py | 5 | [Product] |
| 마케팅 | marketing.py | 4 | [Marketing] |
| 예측 | forecast.py | 3 | [Forecast] |
| 이상치 탐지 | anomaly.py | 2 | [Anomaly] |
| 통계 분석 | stats.py | 11 | [Stats] |
| A/B 테스트 | ab_test.py | 4 | [ABTest] |
| 헬퍼 | helper.py + viz_helper.py + bi_helper.py | 7 | [Helper] |
| 품질/비교 | validation.py + compare.py + cross_source.py | 4 | [Quality][Compare][CrossSource] |
| 알림/설정/컨텍스트 | alerts.py + setup.py + context.py | 9 | [Alert] |
| 외부 연동 (신규) | redash.py, grafana.py, segment.py, dbt_cloud.py | 16 | [Redash][Grafana][Segment][dbtCloud] |

---

## 개발 규칙

### 새 도구 추가 시 필수 패턴

**1. docstring 첫 줄에 카테고리 태그 필수**
```python
def my_tool(conn_id: str, sql: str, ...) -> str:
    """[Stats] 도구 설명 한 줄.
    Args:
        conn_id: DB 연결 ID
        ...
    """
```

**2. _fetch_df 패턴 (try/finally conn.close() 필수)**
```python
def _fetch_df(conn_id: str, sql: str):
    err = _validate_select(sql)
    if err:
        return None, f"[ERROR] {err}"
    if conn_id not in _connections:
        return None, f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."
    try:
        conn = _get_conn(_connections[conn_id])
        try:
            df = pd.read_sql(sql, conn)
            return df, ""
        finally:
            conn.close()
    except Exception as e:
        return None, f"[ERROR] 쿼리 실행 실패: {e}"
```

**3. 에러 반환 형식**: 반드시 `[ERROR]` 접두사
```python
return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
```

**4. scipy dual-path (통계 함수에서 필수)**
```python
try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False
```

**5. server.py 등록 (마지막 if __name__ 블록 바로 앞에 추가)**
```python
# my_tools — 설명
from bi_agent_mcp.tools.my_module import my_tool_a, my_tool_b
mcp.tool()(my_tool_a)
mcp.tool()(my_tool_b)
```

---

## 테스트 규칙

### mock.patch 경로 규칙 (중요!)
```python
# 반드시 tools.모듈명._connections 경로로 패치
@patch("bi_agent_mcp.tools.stats._connections", {"test": MagicMock()})
@patch("bi_agent_mcp.tools.stats._get_conn")
def test_xxx(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    with patch("bi_agent_mcp.tools.stats.pd") as mock_pd:
        mock_pd.read_sql.return_value = pd.DataFrame({...})
```

### 테스트 실행
```bash
# 전체 테스트 (커버리지 게이트 80%)
python3 -m pytest tests/unit/ -q --no-header

# 특정 모듈 테스트
python3 -m pytest tests/unit/test_stats.py -q --no-header

# 도구 수 확인
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
```

### 테스트 작성 기준
- 각 함수당 최소 2개 (정상 케이스 + 에러 케이스)
- 에러 케이스: 잘못된 conn_id, 없는 컬럼명
- DB 없는 헬퍼 함수: mock 불필요, 직접 호출

---

## 분석 흐름 가이드 (어떤 도구를 언제 쓸까?)

### 진입점 (항상 여기서 시작)

| 상황 | 사용할 도구 |
|------|------------|
| 처음 분석 요청 (방법 모름) | `bi_start(query)` |
| 연결 있고 바로 분석 원함 | `bi_start(query, conn_id="...")` |
| 복잡한 분석 직접 제어 | `bi_orchestrate(query, conn_id)` |

### 전체 흐름

```
자연어 요청
    │
bi_start(query, conn_id?)
    │
    ├─ 방법 질문 ("어떻게", "뭐부터") → 가이드 모드
    │   └─ bi_tool_selector() + hypothesis_helper() 반환
    │
    └─ 실행 요청 ("분석해", "왜", "원인") → 오케스트레이터 모드
        └─ bi_orchestrate() 호출
            └─ 스키마 → SQL 컨텍스트 → 도구 안내 → 가설 → 분석 방향 반환
                └─ Claude가 run_query → 분석 도구 → generate_report 순 실행
```

### 데이터 소스별 연결 방법

| 소스 | 도구 |
|------|------|
| PostgreSQL / MySQL / BigQuery | `connect_db` |
| CSV / Excel | `connect_file` |
| Databricks | `connect_databricks` |
| Redash | `connect_redash` |
| Grafana | `connect_grafana` |
| Segment | `connect_segment` |
| dbt Cloud | `connect_dbt_cloud` |
| Airbyte | `connect_airbyte` |
| Mixpanel | `connect_mixpanel` |
| Amplitude | `connect_amplitude` |
| Heap | `connect_heap` |

### BI 출력별 도구

| 출력 형태 | 도구 |
|-----------|------|
| 마크다운 보고서 | `generate_report(sections=[...])` |
| Chart.js HTML 대시보드 | `generate_dashboard(data, charts)` |
| Tableau TWBX | `generate_twbx(data, chart_type, title)` |
| Power BI | `connect_powerbi` → `list_powerbi_reports` |
| QuickSight | `connect_quicksight` → `list_quicksight_dashboards` |

---

## 스킬 (Claude Code 슬래시 명령어)

`.claude/commands/` 에 위치:

| 스킬 | 설명 |
|------|------|
| `/bi-connect` | 데이터 소스 연결 및 컨텍스트 로드 |
| `/bi-explore` | 도메인 맥락 기반 데이터 탐색 |
| `/bi-analyze` | 도메인 인식 기반 심층 분석 |
| `/bi-report` | 종합 BI 리포트 생성 |
| `/bi-domain` | 비즈니스 도메인 컨텍스트 관리 |
| `/bi-stats` | 통계 분석 워크플로우 (기술통계→가설검정) |
| `/bi-ab` | A/B 테스트 전문 (설계→분석→세그먼트→시간효과) |
| `/bi-viz` | 시각화 생성 (Chart.js HTML / Tableau TWBX) |
| `/bi-help` | 도구 선택 가이드 (157개 도구 중 목표별 추천) |

---

## 비즈니스 컨텍스트

`context/` 디렉토리에 도메인 지식 저장:
- `01_business_context.md` — 비즈니스 개요
- `02_data_sources.md` — 데이터 소스 설명
- `03_kpi_dictionary.md` — KPI 정의 및 목표값
- `04_analysis_patterns.md` — 분석 패턴
- `05_glossary.md` — 용어 정의

`load_domain_context(sections="all")` 으로 로드.

---

## 주요 설정

- **QUERY_LIMIT**: 기본 500행 (`BI_AGENT_QUERY_LIMIT` 환경변수로 변경)
- **SELECT 전용**: DML 자동 차단 (`_validate_select`)
- **커버리지 게이트**: 80% (`.coveragerc` 참조)
- **Python**: 3.11 이상 필요
