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
- **BI 분석**: 트렌드, 상관관계, 분포, 세그먼트, 퍼널, 코호트 분석
- **통계 분석**: 기술통계, 추론통계, 가설검정 (t-test, ANOVA, 카이제곱)
- **A/B 테스트**: 샘플 크기, 다변형, 세그먼트 이질 효과, Novelty Effect
- **비즈니스 분석**: 매출, RFM, LTV, 이탈, 파레토, 성장 분석
- **프로덕트 분석**: 활성 사용자, 리텐션, 기능 채택, 사용자 여정
- **마케팅 분석**: 캠페인, 채널 귀인, CAC/ROAS, 전환 퍼널
- **예측 및 이상치**: 시계열 예측, 이상치 탐지
- **분석 오케스트레이션**: 플랜 기반 분석 워크플로우 자동화
- **BI 헬퍼**: 가설검증, 방법론 추천, 결과 해석, 시각화 조언
- **리포트 생성**: 마크다운 리포트, Tableau TWBX, Chart.js 대시보드(HTML)
- **데이터 품질**: 규칙 기반 검증, 알림, 쿼리 비교

### 도구 수

**총 98개 도구** (2025년 3월 기준)

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
2. **데이터베이스 설정** (PostgreSQL/MySQL/BigQuery/Snowflake)
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

또는 BI 분석:

```
"고객 매출의 트렌드를 분석해줄래?"
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

### DB/파일 연결 도구

#### `connect_db(db_type, host, port, database, user, password, ...)`

데이터베이스 연결을 등록합니다.

**파라미터:**
- `db_type`: "postgresql" | "mysql" | "bigquery" | "snowflake"
- `host`: 데이터베이스 호스트
- `port`: 포트 (BigQuery 제외)
- `database`: 데이터베이스 이름
- `user`: 사용자명
- `password`: 비밀번호
- `project_id`: BigQuery 전용

**예시:**
```
"PostgreSQL 연결: host=db.company.com, database=analytics"
```

#### `get_schema(conn_id, table_name)`

테이블 스키마를 조회합니다. (컬럼명, 타입, NULL 가능 여부, 샘플 데이터)

**예시:**
```
"customers 테이블의 스키마를 보여줄래?"
```

#### `run_query(conn_id, sql, limit=500)`

SELECT 쿼리를 실행합니다. (읽기 전용, 최대 500행)

**예시:**
```
"SELECT customer_id, COUNT(*) as order_count FROM orders GROUP BY customer_id LIMIT 10"
```

#### `profile_table(conn_id, table_name)`

테이블을 프로파일링합니다. (NULL 비율, 유니크 값, 최댓값, 상위값, 분포)

**예시:**
```
"customers 테이블을 프로파일링해줄래?"
```

#### `connect_file(file_path)`

CSV/Excel 파일을 로드합니다.

**예시:**
```
"sales_data.csv 파일을 로드해줄래?"
```

#### `query_file(file_id, sql)`

로드된 파일에 SQL 쿼리를 실행합니다.

**예시:**
```
"파일에서 지역별 매출 합계를 조회해줄래?"
```

### 통계 분석 도구

#### 기술통계

`descriptive_stats(data, column)` - 평균, 중앙값, 표준편차, 사분위수

`percentile_analysis(data, column, percentiles=[25, 50, 75, 95])` - 백분위수 분석

`boxplot_summary(data, column)` - 박스플롯 요약 (IQR, 수염, 이상치)

**예시:**
```
"고객의 주문 금액 분포를 분석해줄래?"  → descriptive_stats
"매출의 P95를 계산해줄래?"  → percentile_analysis
```

#### 추론통계

`confidence_interval(data, column, confidence=0.95)` - 신뢰구간 (95%, 99%)

`sampling_error(population_size, sample_size, proportion)` - 표본 오차 계산

**예시:**
```
"고객 만족도의 95% 신뢰구간을 구해줄래?"
"필요한 표본 크기는 얼마일까?"  → sampling_error
```

#### 가설검정

**1표본 t-검정:**
`ttest_one_sample(data, column, test_value)` - 모집단 평균과 비교

**예시:**
```
"평균 주문액이 100을 초과하는지 검정해줄래?"
```

**2표본 t-검정:**
`ttest_independent(data1, data2, column)` - 두 그룹 비교

**예시:**
```
"A 그룹과 B 그룹의 전환율이 다른지 검정해줄래?"
```

**대응 표본 t-검정:**
`ttest_paired(data_before, data_after, column)` - 쌍을 이룬 데이터 비교

**예시:**
```
"캠페인 전후 평균 주문액이 달라졌는지 검정해줄래?"
```

**분산분석 (ANOVA):**
`anova_one_way(data, group_column, value_column)` - 3개 이상 그룹 비교

**예시:**
```
"지역별(A/B/C) 평균 매출이 다른지 검정해줄래?"
```

**카이제곱 검정:**
`chi_square_test(data, column1, column2)` - 범주형 변수 독립성 검정

**예시:**
```
"구매여부와 성별이 독립인지 검정해줄래?"
```

**정규성 검정:**
`normality_test(data, column)` - Shapiro-Wilk, Kolmogorov-Smirnov 검정

**예시:**
```
"주문액이 정규분포를 따르는지 검정해줄래?"
```

### A/B 테스트 전문 도구

#### `ab_sample_size(alpha=0.05, beta=0.20, baseline_rate, mde)`

필요 표본 크기 계산

**파라미터:**
- `alpha`: 유의수준 (기본 0.05)
- `beta`: 타입 II 오류 (기본 0.20, 검정력 80%)
- `baseline_rate`: 기존 전환율 (0~1 사이)
- `mde`: 최소 효과 크기 (실무적 의미 있는 개선율)

**예시:**
```
"전환율이 2%에서 2.2%로 개선되는지 검정하려면 표본은 얼마나 필요할까?"
→ ab_sample_size(baseline_rate=0.02, mde=0.1)  # 10% 상대개선
```

#### `ab_test_analysis(control_data, treatment_data, metric_column)`

2 그룹 A/B 테스트 통계 분석

**산출:**
- 각 그룹의 평균/분산
- 효과 크기 (Cohen's d)
- t-검정 p-value 및 유의성
- 신뢰도 95% 신뢰구간

**예시:**
```
"A와 B의 전환율이 유의하게 다른가?"
→ ab_test_analysis(control_data, treatment_data, metric_column='converted')
```

#### `ab_multivariate(groups_data, metric_column)`

A/B/C/n 다변형 실험 분석

**특징:**
- 다중 비교 보정 (Bonferroni)
- ANOVA로 전체 효과 검정
- 사후 검정(Post-hoc)으로 쌍별 비교

**예시:**
```
"A/B/C/D 4가지 변형 중 어느 것이 가장 좋은가?"
```

#### `ab_segment_breakdown(data, metric_column, segment_column)`

세그먼트별 이질 효과(HTE, Heterogeneous Treatment Effect) 분석

**산출:**
- 전체 효과
- 각 세그먼트별 효과 크기
- 세그먼트 간 상호작용 여부

**예시:**
```
"신규고객 vs 기존고객에서 처치 효과가 다른가?"
```

#### `ab_time_decay(time_series_data, metric_column, date_column, treatment_start_date)`

시간에 따른 효과 변화 및 Novelty Effect 분석

**특징:**
- 일별/주별 효과 크기 변화 추적
- Novelty Effect 감지 (초반 높은 효과 후 감소)
- 안정화 시점 판단

**예시:**
```
"이 기능 출시 후 효과가 지속되나, 아니면 초반에만 좋은가?"
```

### BI 심층 분석 도구

#### `trend_analysis(data, date_column, value_column, period="day")`

시계열 트렌드 분석 (증감, 변동률, 전기비 등)

**예시:**
```
"매출의 월별 트렌드를 분석해줄래?"
```

#### `correlation_analysis(data, columns)`

변수 간 상관관계 분석 (Pearson, Spearman)

**예시:**
```
"광고비와 매출의 상관관계는?"
```

#### `distribution_analysis(data, column)`

데이터 분포 분석 (정규/왜도/첨도)

**예시:**
```
"고객 주문액의 분포 특성을 분석해줄래?"
```

#### `segment_analysis(data, segment_column, metric_column)`

세그먼트별 비교 분석

**예시:**
```
"지역별 평균 주문액을 비교해줄래?"
```

#### `funnel_analysis(data, step_column, value_column)`

퍼널 단계별 이탈률 분석

**예시:**
```
"가입 → 첫구매 → 재구매 퍼널을 분석해줄래?"
```

#### `cohort_analysis(data, cohort_column, date_column, metric_column, interval="month")`

코호트별 행동 패턴 분석

**예시:**
```
"월별 신규 고객의 리텐션을 분석해줄래?"
```

#### `pivot_table(data, index, columns, values, aggfunc="sum")`

피벗테이블 생성 (집계, 교차분석)

#### `top_n_analysis(data, group_column, metric_column, n=10)`

상위 N개 항목 추출 및 순위 분석

### 분석 오케스트레이션 도구

복잡한 분석을 여러 단계로 나누어 자동화합니다.

#### `create_analysis_plan(title, objective, steps)`

분석 플랜 생성

**파라미터:**
- `title`: 분석 제목
- `objective`: 분석 목표
- `steps`: 단계별 분석 방법 (배열)

**예시:**
```
"고객 이탈 분석" 플랜 생성:
1. 이탈 고객 정의 및 분류
2. 이탈 고객의 특성 분석 (세그먼트)
3. 이탈 사유 분석 (상관관계, 분포)
4. 리스크 스코어링 (RFM)
```

#### `get_analysis_plan(plan_id)`

저장된 분석 플랜 조회

#### `add_analysis_step(plan_id, step_name, description)`

플랜에 단계 추가

#### `update_analysis_step(plan_id, step_id, status, result, interpretation)`

단계 업데이트 (상태, 결과, 해석)

**상태:** pending, in_progress, completed, failed

#### `synthesize_findings(plan_id)`

모든 단계 결과를 통합 정리

#### `list_analysis_plans()`

저장된 분석 플랜 목록

#### `complete_analysis_plan(plan_id)`

분석 플랜 완료 처리

### BI/분석 헬퍼 도구

#### `hypothesis_helper(business_context, metric)`

가설 검증 프레임워크 가이드

**산출:**
- 귀무 가설(H0) 및 대립 가설(H1) 수립
- 검정 방법 추천
- 필요 표본 크기 및 기간 추정

**예시:**
```
"고객 만족도 개선 효과를 검증하려면 어떻게 해야 할까?"
```

#### `analysis_method_recommender(data_type, research_question)`

데이터 특성에 맞는 분석 방법론 추천

**고려 요소:**
- 데이터 타입 (수치/범주)
- 표본 크기
- 정규성 여부
- 변수 개수

**예시:**
```
"비정규 분포 데이터를 비교하려면?"
→ Mann-Whitney U 검정, Kruskal-Wallis 검정 추천
```

#### `query_result_interpreter(query_result, context)`

쿼리 결과 해석 및 인사이트 도출

**산출:**
- 주요 수치와 패턴 요약
- 비즈니스 의미 해석
- 후속 분석 제안

**예시:**
```
"이 매출 쿼리 결과를 해석해줄래?"
```

#### `tableau_viz_guide(metric_type, data_volume)`

Tableau 시각화 모범 사례 및 사용 가이드

**산출:**
- 권장 차트 타입
- 색상 팔레트
- 대시보드 레이아웃

#### `visualize_advisor(data, columns)`

데이터 특성에 맞는 시각화 방법 추천

**고려 요소:**
- 데이터 차원 (1D/2D/3D+)
- 데이터 분포
- 비교 vs 추이 vs 구성

#### `dashboard_design_guide(kpis, audience)`

대시보드 레이아웃, 색상, 상호작용 설계 가이드

#### `bi_tool_selector(business_goal, data_characteristics)`

분석 목표별 98개 도구 중 추천 도구 선택

**예시:**
```
"고객 이탈을 분석하려면 어떤 도구를 써야 할까?"
→ churn_analysis, cohort_analysis, rfm_analysis 등 추천
```

---

## 실전 시나리오

### 시나리오 1: A/B 테스트 워크플로우

목표: 새 UI의 전환율 개선 효과 검정

**1단계: 필요 표본 크기 계산**
```
"현재 전환율이 5%인데, 5.5%로 개선되는지 검정하려면 표본은 얼마나 필요할까?"
→ ab_sample_size(baseline_rate=0.05, mde=0.1)  # 10% 상대개선
결과: ~21,550명 필요 (그룹당)
```

**2단계: 기본 A/B 테스트 분석**
```
"A 그룹(기존 UI)과 B 그룹(신 UI)의 전환율을 비교해줄래?"
→ ab_test_analysis(control_data, treatment_data, metric_column='converted')
```

**3단계: 세그먼트별 효과 분석**
```
"신규고객 vs 기존고객에서 효과가 다른가?"
→ ab_segment_breakdown(data, 'converted', 'customer_type')
```

**4단계: 시간에 따른 효과 변화**
```
"출시 후 1개월간 효과가 지속되나?"
→ ab_time_decay(daily_data, 'converted', 'date', '2025-03-01')
```

### 시나리오 2: 통계 분석 워크플로우

목표: 상품 A와 B의 평균 가격 차이 검정

**1단계: 기술통계로 기본 패턴 파악**
```
"상품 A와 B의 가격 분포를 분석해줄래?"
→ descriptive_stats(data, 'price')
→ boxplot_summary(data, 'price')
```

**2단계: 정규성 검정 (어떤 검정을 할지 판단)**
```
"가격이 정규분포를 따르나?"
→ normality_test(data, 'price')
→ 정규: t-검정 / 비정규: Mann-Whitney U 검정
```

**3단계: 가설검정**
```
"상품 A의 평균 가격이 10000을 초과하는가?"
→ ttest_one_sample(data, 'price', test_value=10000)

"상품 A와 B의 평균 가격이 다른가?"
→ ttest_independent(data_a, data_b, 'price')
```

**4단계: 신뢰도 제시**
```
"상품 A 평균 가격의 95% 신뢰구간은?"
→ confidence_interval(data_a, 'price', confidence=0.95)
```

### 시나리오 3: 고객 이탈 분석 (오케스트레이션)

목표: 고객 이탈 원인 파악 및 위험도 점수화

**1단계: 분석 플랜 생성**
```
create_analysis_plan(
  title="고객 이탈 분석",
  objective="이탈 고객의 특성 파악 및 위험도 판단",
  steps=[
    "이탈 고객 정의 (마지막 구매 후 180일 이상 미구매)",
    "이탈 고객의 인구통계/행동 특성 분석",
    "RFM 분석으로 위험도 점수화",
    "코호트 분석으로 연령대별 이탈 추이 추적",
    "이탈 사유 상관관계 분석"
  ]
)
```

**2단계: 각 단계 실행**
```
# 단계 1: 고객 이탈 정의
add_analysis_step(..., "이탈 고객 정의", "...")
update_analysis_step(..., status="completed", result="5,234명 이탈 확인")

# 단계 2: 특성 분석
add_analysis_step(..., "특성 분석", "...")
→ segment_analysis(data, 'region', 'churn_rate')
→ correlation_analysis(data, ['age', 'avg_order_value', 'churn'])

# 단계 3: RFM 분석
add_analysis_step(..., "RFM 분석", "...")
→ rfm_analysis(data)

# 단계 4: 코호트 분석
add_analysis_step(..., "코호트 분석", "...")
→ cohort_analysis(data, 'signup_month', 'date', 'is_active')
```

**3단계: 결과 통합**
```
synthesize_findings(plan_id)
→ 주요 발견: 3개월 이상 미활성 고객의 80%가 이탈
→ 액션: 3개월 타겟 재참여 캠페인 필요
```

### 시나리오 4: 매출 분석

목표: 월별 매출 추이 분석 및 예측

**1단계: 트렌드 분석**
```
"월별 매출 추이를 분석해줄래?"
→ trend_analysis(data, 'date', 'revenue', period='month')
```

**2단계: 시계열 예측**
```
"앞으로 3개월 매출을 예측해줄래?"
→ moving_average_forecast(historical_data, periods=3)
→ exponential_smoothing_forecast(historical_data, periods=3)
```

**3단계: 아웃풋 생성**
```
"분석 결과를 대시보드로 만들어줄래?"
→ generate_dashboard(data, queries=[revenue_by_month, forecast])

"리포트로 정리해줄래?"
→ generate_report(findings, output_format='markdown')
```

---

## 비즈니스 컨텍스트 설정

비즈니스 도메인 지식을 제공하면 AI의 분석 제안이 더 정확해집니다.

### context/ 디렉토리 구조

```
context/
├── README.md
├── business.md          # 비즈니스 목표, KPI, 우선순위
├── products.md          # 제품 정보, 기능, 버전
├── customers.md         # 고객 세그먼트, 페르소나
├── data_catalog.md      # 데이터베이스, 테이블, 의미
├── metrics.md           # 정의된 메트릭, 계산식
└── events.md            # 추적 이벤트, 정의
```

### business.md 예시

```markdown
# 비즈니스 컨텍스트

## 회사 소개
- 이름: Acme Inc.
- 산업: SaaS (프로젝트 관리)
- 주요 고객: 중소 기업 (직원 10~1,000명)

## 비즈니스 목표
- 2025년 ARR 100M 달성
- 고객 이탈률 5% 이하 유지
- 고객 만족도 NPS 50+ 달성

## 주요 KPI
- MRR (Monthly Recurring Revenue)
- Churn Rate (월 고객 이탈률)
- CAC (Customer Acquisition Cost)
- LTV (Lifetime Value)
- NPS (Net Promoter Score)

## 최근 이슈
- Q1: 신규 고객 확보 둔화
- Q2: 기존 고객 이탈 증가 추세
```

### metrics.md 예시

```markdown
# 메트릭 정의

## 활성 사용자 (Active Users)
- DAU: 일일 활성 사용자 (로그인 또는 API 호출)
- WAU: 주간 활성 사용자
- MAU: 월간 활성 사용자

## 이탈 (Churn)
- 정의: 마지막 구독료 납부 후 30일 이상 미갱신
- 계산: churn_user / prev_month_user
- 목표: < 5%

## LTV
- 정의: 신규 고객의 평생 순이익
- 계산: average_monthly_profit * (1 / monthly_churn_rate)
```

---

## 보안

### 핵심 보안 원칙

- **SELECT 전용**: DML 쿼리(INSERT, UPDATE, DELETE, DROP 등) 자동 차단
- **결과 행 제한**: 기본 500행 제한 (환경 변수로 조정 가능)
- **로컬 처리 보장**: 모든 데이터는 사용자 로컬 머신 또는 사내 네트워크에서만 처리
- **자격증명 보호**: 평문 로그 기록 없음, 민감한 정보는 마스킹됨

### 자격증명 저장

- **환경 변수**: 권장 방식 (`.env` 파일 사용 가능)
- **OS 키체인**: OAuth 토큰 저장 (macOS Keychain, Linux libsecret, Windows Credential Manager)
- **설정 파일**: 민감한 정보는 절대 설정 파일에 저장하지 마세요

### 데이터 개인정보보호

- 쿼리 결과는 로컬 메모리에서만 처리되며 디스크에 저장되지 않음
- LLM API로는 텍스트 표현만 전송되고 원본 데이터는 전송되지 않음
- 저장된 쿼리는 SQL 텍스트만 저장하며 결과 데이터는 저장하지 않음

---

## 문제 해결

### 연결 문제

**증상**: "데이터베이스에 연결할 수 없습니다"

**해결책**:
1. 환경 변수 확인: `echo $BI_AGENT_PG_HOST`
2. 데이터베이스 접근성 테스트: `nc -zv db.company.com 5432`
3. 자격증명 확인: 사용자명, 비밀번호, 포트
4. 방화벽 규칙 확인

```bash
# 데이터베이스 도구로 테스트
test_datasource(db_type='postgresql', host='...', ...)
```

### 쿼리 실행 오류

**증상**: "쿼리 실행 실패: Syntax Error"

**해결책**:
1. SQL 문법 검증: 공백, 따옴표, 테이블/컬럼명 확인
2. 테이블 존재 여부: `get_schema(conn_id, table_name)`
3. 컬럼명 확인: `SELECT * FROM table_name LIMIT 1`

```bash
# AI에 쿼리 생성 요청
"SELECT 지난 30일 일별 매출을 구해줄래?"
→ generate_sql()로 자동 생성 가능
```

### 통계 분석 결과 해석

**증상**: "p-value가 0.05보다 크다고 나왔는데 뭐라는 거예요?"

**해결책**:
```
p-value > 0.05 → 귀무 가설 채택 (두 그룹 간 유의한 차이 없음)
p-value < 0.05 → 귀무 가설 기각 (두 그룹 간 유의한 차이 있음)

예시:
"A와 B의 전환율 t-검정 결과: p-value=0.15"
→ 해석: 두 그룹 간 전환율 차이는 통계적으로 유의하지 않음 (표본 부족 가능)
→ 조치: 표본 크기 증가, 기간 연장
```

### 성능 문제

**증상**: "대용량 데이터 쿼리가 느립니다"

**해결책**:
1. 행 제한 사용: `LIMIT 500` (기본값)
2. 필터 추가: `WHERE created_date > '2025-01-01'`
3. 캐시 활용: 자주 쓰는 쿼리 저장 → `run_saved_query()`
4. 캐시 초기화: `clear_cache(conn_id)`

```bash
# 대용량 데이터는 샘플링
"고객 1,000만 명 중 임의로 10,000명을 뽑아서 분석해줄래?"
→ stratified sampling 권장
```

### 라이센스/버전 문제

**증상**: "모듈을 찾을 수 없다" 또는 "버전 호환 오류"

**해결책**:
```bash
# 설치 확인
python -c "import bi_agent_mcp; print(bi_agent_mcp.__version__)"

# 의존성 재설치
pip install --upgrade bi-agent-mcp

# 개발 모드 재설치
cd /path/to/bi-agent
pip install -e . --force-reinstall
```

---

**문서 버전**: 2025-03-26
**도구 수**: 98개
**최근 업데이트**: A/B 테스트 워크플로우, 통계 분석 도구 추가
