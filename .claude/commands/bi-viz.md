# /bi-viz — 데이터 시각화 생성

분석 결과를 Chart.js 대시보드(HTML) 또는 Tableau TWBX 파일로 시각화합니다.
어떤 차트가 적합한지 모르면 자동으로 추천합니다.

## 실행 절차

### 1단계: 시각화 목표 파악

1. $ARGUMENTS에서 시각화 목표 파악
   - 없으면: "어떤 데이터를 시각화하고 싶으신가요?" 질문
2. `visualize_advisor(data_columns=[...], analysis_goal="...")` 실행
   - 권장 출력 도구 (Chart.js vs Tableau) 및 차트 타입 확인

### 2단계: 데이터 준비

3. `list_connections`으로 연결 확인
4. `run_query(conn_id, sql)` 또는 `query_file(file_id, sql)`로 데이터 조회
   - 결과가 마크다운 테이블 형식으로 반환됨

### 3단계: 시각화 생성

**Chart.js 대시보드 (웹 브라우저에서 바로 열 수 있는 HTML)**:

- `dashboard_design_guide(kpi_metrics=[...], dimension_cols=[...], time_col="...")` 실행
  - charts 파라미터 구성 안내 받기
- `generate_dashboard(conn_id, queries=[...], title="...")` 실행

**Tableau TWBX (Tableau Desktop에서 열 수 있는 패키지)**:

- `tableau_viz_guide(chart_goal="...", data_columns=[...])` 실행
  - chart_type 및 Tableau 설정 가이드 확인
- `generate_twbx(data="...마크다운 테이블...", chart_type="auto", title="...")` 실행

**파일 데이터 시각화**:

- `chart_from_file(file_id, chart_configs=[...], title="...")` 실행

### 4단계: 결과 안내

5. 생성된 파일 경로 안내
6. Chart.js의 경우: 브라우저에서 바로 열기 가능
7. TWBX의 경우: Tableau Desktop 열기 절차 안내

## 차트 선택 가이드

| 데이터 특성 | 권장 차트 |
|-----------|---------|
| 날짜 + 수치 | Line (시계열) |
| 범주 + 수치 | Bar (비교) |
| 수치 + 수치 | Scatter (상관관계) |
| 비율/구성 | 마크다운 테이블 후 Bar |
| KPI 강조 | KPI 카드 + Bar |

## 사용법

```
/bi-viz                                  # 가이드 모드
/bi-viz 월별 매출 추이 차트 만들어줘        # 시계열 라인 차트
/bi-viz 카테고리별 매출 대시보드            # 바 차트 대시보드
/bi-viz tableau로 상관관계 시각화          # Tableau TWBX
/bi-viz 엑셀 파일로 대시보드 생성          # 파일 기반 대시보드
```

## 사용 MCP 도구

- `visualize_advisor(data_columns, analysis_goal, output_format)` — 시각화 방법 추천
- `dashboard_design_guide(kpi_metrics, dimension_cols, time_col)` — 대시보드 레이아웃 설계
- `generate_dashboard(conn_id, queries, title)` — Chart.js HTML 대시보드 생성
- `generate_twbx(data, chart_type, title)` — Tableau TWBX 패키지 생성
- `chart_from_file(file_id, chart_configs, title)` — 파일 데이터 차트 생성
- `tableau_viz_guide(chart_goal, data_columns, detail_level)` — Tableau 사용 가이드
- `run_query(conn_id, sql)` — 데이터 조회
- `list_connections` — 연결 확인
