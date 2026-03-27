<h1 align="center">bi-agent MCP: The AI-Native BI Analytics Engine</h1>

<p align="center">
  <strong>"데이터에게 질문하라. AI가 분석하고, 당신이 결정한다."</strong><br />
  bi-agent는 단순한 쿼리 도구를 넘어, Claude Desktop · Cursor · VSCode · Antigravity 등<br />
  MCP를 지원하는 모든 AI 클라이언트에서 <strong>98개 분석 도구</strong>를 자연어 하나로 구동하는<br />
  <strong>AI-Native BI 분석 엔진</strong>입니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge&logo=statuspage" alt="Status" />
  <img src="https://img.shields.io/badge/Protocol-MCP-4285F4?style=for-the-badge&logo=anthropic" alt="MCP" />
  <img src="https://img.shields.io/badge/Tools-98개-orange?style=for-the-badge" alt="Tools" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 🏛️ Comprehensive Analytics Suite

bi-agent는 데이터 분석의 전 과정을 커버하는 98개 MCP 도구를 카테고리별로 제공합니다.

### 🔌 데이터 소스 연결 (14개)

**모든 데이터 소스에 하나의 프로토콜로 연결합니다.**

- **다중 DB**: PostgreSQL, MySQL, BigQuery, Snowflake 연결 및 읽기 전용 쿼리 실행
- **파일 분석**: CSV · Excel 파일을 로드해 DuckDB/pandasql로 직접 쿼리
- **외부 SaaS**: Google Analytics 4, Amplitude 이벤트 데이터 실시간 조회
- **멀티 소스 조인**: DB와 파일 데이터를 DuckDB로 크로스조인 분석

### 📊 BI 심층 분석 (53개+)

**비즈니스 의사결정에 필요한 모든 분석을 한 곳에서.**

- **비즈니스 분석**: 매출 추이, RFM, LTV, 고객 이탈, 파레토, 성장률 분석
- **프로덕트 분석**: DAU/WAU/MAU, 리텐션 곡선, 기능 채택율, 사용자 여정
- **마케팅 분석**: 캠페인 성과, 채널 귀인(first/last/multi-touch), CAC/ROAS, 전환 퍼널
- **통계 분석**: 기술통계, t-검정, ANOVA, 카이제곱, 신뢰구간, 정규성 검정
- **A/B 테스트 전문**: 샘플 크기 계산, 다변형 실험(A/B/C/n), 세그먼트 이질 효과(HTE), Novelty Effect 감지
- **시계열 예측**: 이동평균, 지수평활, 선형 추세 예측
- **이상치 탐지**: IQR, Z-score 기반 이상값 자동 검출

### 🤖 AI 헬퍼 & 오케스트레이션 (15개+)

**분석 설계부터 결과 해석까지, AI가 함께합니다.**

- **분석 플랜**: 목표 기반 분석 워크플로우 자동 설계 및 단계별 진척 관리
- **Text-to-SQL**: 자연어 질문으로 복잡한 SQL 즉시 생성
- **방법론 추천**: 데이터 특성에 맞는 분석 방법 및 도구 자동 추천
- **아웃풋 생성**: 마크다운 리포트, Tableau TWBX, Chart.js 인터랙티브 대시보드 자동 생성

---

## 📖 Quick Start

### 1단계: 설치

Python 3.11 이상이 필요합니다.

```bash
pip install bi-agent-mcp
```

또는 개발 모드:

```bash
git clone https://github.com/your-org/bi-agent.git
cd bi-agent
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -e .
```

### 2단계: 클라이언트 설정

#### 자동 설정 (권장)

설치 후 아래 명령어 하나로 모든 설정을 완료할 수 있습니다:

```bash
python -m bi_agent_mcp setup
```

또는:

```bash
bi-agent setup  # pip install로 설치한 경우
```

대화형 마법사가 시작되며:
- AI 클라이언트 선택 (Claude Desktop / Cursor / VSCode / Antigravity)
- 데이터 소스 연결 정보 입력 (여러 개 등록 가능)
- 클라이언트 설정 파일 자동 업데이트

#### 수동 설정

<details>
<summary>직접 설정 파일을 편집하려면 클릭</summary>

**Claude Desktop** — `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "bi_user",
        "BI_AGENT_PG_PASSWORD": "your_password"
      }
    }
  }
}
```

| 클라이언트 | 설정 파일 경로 | 문서 |
|--|--|--|
| Cursor | `.cursor/mcp.json` | [가이드](./docs/clients/) |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` | [가이드](./docs/clients/antigravity.md) |
| VSCode Copilot | `.vscode/mcp.json` | [가이드](./docs/clients/) |

</details>

### 3단계: 분석 시작

클라이언트에서 자연어로 대화하세요.

```
"지난 30일간 매출 상위 10개 상품을 분석하고 전월 대비 성장률을 알려줘"
"사용자 이탈 원인을 RFM 분석으로 세그먼트별로 파악해줘"
"A/B 테스트 결과가 통계적으로 유의미한지 검정해줘"
```

더 자세한 사용법은 [워크플로우 가이드](./docs/WORKFLOW.md)를 참고하세요.

---

## 🔧 환경 변수

모든 환경 변수는 `BI_AGENT_` 접두사를 사용합니다.

<details>
<summary><strong>PostgreSQL / MySQL / BigQuery / Snowflake</strong></summary>

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `BI_AGENT_PG_HOST` | PostgreSQL 호스트 | N |
| `BI_AGENT_PG_PORT` | PostgreSQL 포트 (기본 5432) | N |
| `BI_AGENT_PG_DBNAME` | PostgreSQL DB명 | Y* |
| `BI_AGENT_PG_USER` | PostgreSQL 사용자명 | Y* |
| `BI_AGENT_PG_PASSWORD` | PostgreSQL 비밀번호 | Y* |
| `BI_AGENT_MYSQL_HOST` | MySQL 호스트 | N |
| `BI_AGENT_MYSQL_DBNAME` | MySQL DB명 | Y* |
| `BI_AGENT_MYSQL_USER` | MySQL 사용자명 | Y* |
| `BI_AGENT_MYSQL_PASSWORD` | MySQL 비밀번호 | Y* |
| `BI_AGENT_BQ_PROJECT_ID` | BigQuery GCP 프로젝트 ID | Y* |
| `BI_AGENT_BQ_DATASET` | BigQuery 데이터셋명 | Y* |
| `BI_AGENT_BQ_CREDENTIALS_PATH` | BigQuery 서비스 계정 키 경로 | Y* |
| `BI_AGENT_SF_ACCOUNT` | Snowflake 계정 ID | Y* |
| `BI_AGENT_SF_USER` | Snowflake 사용자명 | Y* |
| `BI_AGENT_SF_PASSWORD` | Snowflake 비밀번호 | Y* |
| `BI_AGENT_SF_DATABASE` | Snowflake DB명 | Y* |
| `BI_AGENT_SF_WAREHOUSE` | Snowflake 웨어하우스명 | Y* |

> Y* = 해당 데이터 소스를 사용할 때 필수

</details>

<details>
<summary><strong>외부 SaaS (GA4 / Amplitude)</strong></summary>

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `BI_AGENT_GOOGLE_CLIENT_ID` | GA4 OAuth 클라이언트 ID | Y* |
| `BI_AGENT_GOOGLE_CLIENT_SECRET` | GA4 OAuth 클라이언트 시크릿 | Y* |
| `BI_AGENT_AMPLITUDE_API_KEY` | Amplitude API 키 | Y* |
| `BI_AGENT_AMPLITUDE_SECRET_KEY` | Amplitude 시크릿 키 | Y* |
| `BI_AGENT_QUERY_LIMIT` | 쿼리 결과 최대 행 수 (기본 500) | N |

</details>

---

## 🛠️ MCP 도구 목록 (98개)

| 카테고리 | 도구 수 | 주요 도구 |
|--|--|--|
| DB/파일 연결 | 10 | `connect_db`, `run_query`, `connect_file`, `query_file` |
| 외부 데이터 소스 | 4 | `connect_ga4`, `get_ga4_report`, `connect_amplitude`, `get_amplitude_events` |
| 분석/리포트 | 9 | `suggest_analysis`, `generate_report`, `save_query`, `generate_sql` |
| 아웃풋 생성 | 4 | `generate_twbx`, `generate_dashboard`, `chart_from_file` |
| 데이터 품질/비교 | 4 | `validate_data`, `compare_queries`, `cross_query` |
| 설정/알림 | 11 | `configure_datasource`, `create_alert`, `check_alerts` |
| BI 심층 분석 | 8 | `trend_analysis`, `correlation_analysis`, `funnel_analysis`, `cohort_analysis` |
| 분석 오케스트레이션 | 8 | `create_analysis_plan`, `update_analysis_step`, `synthesize_findings` |
| 비즈니스 분석 | 6 | `revenue_analysis`, `rfm_analysis`, `ltv_analysis`, `churn_analysis` |
| 프로덕트 분석 | 5 | `active_users`, `retention_curve`, `feature_adoption`, `user_journey` |
| 마케팅 분석 | 4 | `campaign_performance`, `channel_attribution`, `cac_roas` |
| 시계열 예측 | 3 | `moving_average_forecast`, `exponential_smoothing_forecast`, `linear_trend_forecast` |
| 이상치 탐지 | 2 | `iqr_anomaly_detection`, `zscore_anomaly_detection` |
| 통계 분석 | 11 | `ttest_independent`, `anova_one_way`, `chi_square_test`, `confidence_interval` |
| A/B 테스트 | 5 | `ab_test_analysis`, `ab_sample_size`, `ab_multivariate`, `ab_segment_breakdown` |
| BI/분석 헬퍼 | 7 | `hypothesis_helper`, `analysis_method_recommender`, `bi_tool_selector` |

전체 도구 상세 설명은 [사용자 매뉴얼](./docs/MANUAL.md)을 참고하세요.

---

## 🔐 보안

- **SELECT 전용**: DML 쿼리(INSERT, UPDATE, DELETE, DROP 등) 자동 차단
- **결과 행 제한**: 기본 500행 제한 (환경 변수로 조정 가능)
- **로컬 처리 보장**: 모든 데이터는 사용자 로컬 머신 또는 사내 네트워크에서만 처리
- **자격증명 보호**: 평문 로그 기록 없음, 민감한 정보는 마스킹됨
- **OS 키체인 지원**: OAuth 토큰은 macOS Keychain / Linux libsecret / Windows Credential Manager에 저장

---

## 🧪 테스트

```bash
# 전체 단위 테스트 실행
pytest tests/unit/

# 커버리지 리포트 포함
pytest tests/unit/ --cov=bi_agent_mcp --cov-report=term-missing
```

- `tests/unit/` — 500+ 단위 테스트, 80% 커버리지 게이트 (pytest-cov)
- `.coveragerc` — 외부 의존 파일(server.py, setup_cli.py, oauth.py) 측정 제외

---

## 📖 문서

- [**DESIGN.md**](./docs/DESIGN.md): 시스템 아키텍처 및 MCP 도구 명세
- [**MANUAL.md**](./docs/MANUAL.md): 도구별 상세 가이드 및 실전 시나리오
- [**Antigravity 설정 가이드**](./docs/clients/antigravity.md): Antigravity 클라이언트 전용 설정

---

## 🤝 지원

문제가 발생하면 [GitHub Issues](https://github.com/your-org/bi-agent/issues)에서 다음 정보와 함께 이슈를 생성해 주세요.

- Python 버전 (`python --version`)
- 설치 방식 (pip / git clone)
- 사용 중인 클라이언트 (Claude Desktop, Cursor, VSCode, Antigravity)
- 오류 메시지 전문

---

Copyright © 2026 bi-agent Contributors. Licensed under the [MIT License](./LICENSE).
