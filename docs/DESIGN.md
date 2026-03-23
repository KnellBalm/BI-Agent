# bi-agent MCP 서버 상세 설계 문서

> 버전: 0.1 | 작성일: 2026-03-18 | 상태: 초안

---

## 목차

1. [제품 개요](#1-제품-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [MCP Tool 명세](#3-mcp-tool-명세)
4. [인증 & 자격증명 관리](#4-인증--자격증명-관리)
5. [설치 & 배포](#5-설치--배포)
6. [데이터 보안](#6-데이터-보안)
7. [기존 코드 재사용 계획](#7-기존-코드-재사용-계획)
8. [버전별 로드맵](#8-버전별-로드맵)
9. [기술 스택](#9-기술-스택)
10. [파일 구조](#10-파일-구조)

---

## 1. 제품 개요

### 한 줄 정의

> **bi-agent**는 분석가·마케터·데이터 엔지니어가 사용하는 AI 클라이언트(Claude, Cursor 등)에 BI 작업 도구를 제공하는 MCP 서버다.

### 타겟 사용자 페르소나

| #   | 페르소나            | 상황                                                                          | bi-agent가 해결하는 것                                   |
| --- | ------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| 1   | **데이터 분석가**   | SQL은 쓸 줄 알지만 매번 스키마 파악, 쿼리 초안, 보고서 포맷에 시간을 낭비     | 스키마 자동 파악, SELECT 초안 생성, 마크다운 보고서 초안 |
| 2   | **디지털 마케터**   | GA4·Amplitude 데이터를 보고 싶지만 개발팀에 요청해야 함, SQL 모름             | 자연어로 GA4/Amplitude 데이터 조회, 지표 초안 생성       |
| 3   | **데이터 엔지니어** | 데이터 파이프라인 프로파일링 자동화 필요, DW/DM/View 등 생성 편의성 확보 필요 | 쿼리튜닝, 테이블 DDL 생성, 파이프라인 최적화             |

### 해결하는 문제 vs 해결하지 않는 문제

```
해결하는 문제                         해결하지 않는 문제
─────────────────────────────────     ────────────────────────────────
- 스키마 파악에 드는 반복 시간         - 완성된 대시보드/리포트 자동 게시
- SQL 초안 작성 (구조·필터·집계)       - 데이터 파이프라인 자동 배포
- GA4/Amplitude 데이터 접근 장벽       - BI 도구(Tableau/Looker) 완전 대체
- Tableau 워크북 빈 초안 작업          - 데이터 품질 자동 보정
- 분석 방향 결정에 드는 시간           - 비즈니스 의사결정 자동화
```

### 핵심 가치 제안

1. **초안 생성으로 업무 시간 단축** — 보고서·쿼리·워크북을 완성본이 아닌 검토 가능한 초안으로 빠르게 생성한다. 최종 판단은 항상 사람이 한다.
2. **사용자 LLM 자유 선택 (BYOLLM)** — Claude Desktop, Cursor, VSCode Copilot, 사내 Ollama 등 MCP를 지원하는 어떤 클라이언트에서도 동일하게 동작한다.
3. **데이터 회사 인프라 밖 반출 금지** — MCP 서버는 사용자 로컬 또는 사내 서버에서 실행된다. 쿼리 결과는 LLM 컨텍스트 안에만 존재하며 외부 서버로 전송되지 않는다.

---

## 2. 시스템 아키텍처

### 전체 흐름 다이어그램

```
사용자 (분석가/마케터/엔지니어)
        │
        │  자연어 질문
        ▼
┌─────────────────────────────────┐
│   LLM 클라이언트                 │  ← Claude Desktop / Cursor / VSCode Copilot / Antigravity
│   (BYOLLM: 사용자가 선택)        │
└────────────┬────────────────────┘
             │  MCP Protocol (JSON-RPC over stdio)
             │  도구 호출 요청 / 결과 수신
             ▼
┌─────────────────────────────────┐
│   bi-agent MCP 서버              │  ← 로컬 또는 사내 서버에서 실행
│   (FastMCP 기반 Python 프로세스) │
│                                 │
│  ┌──────────┐  ┌─────────────┐  │
│  │ tools/   │  │ auth/       │  │
│  │  db.py   │  │  oauth.py   │  │
│  │  ga4.py  │  │  creds.py   │  │
│  │  amp.py  │  └─────────────┘  │
│  │  tab.py  │                   │
│  │  ana.py  │  ┌─────────────┐  │
│  └──────────┘  │ config.py   │  │
│                └─────────────┘  │
└────┬──────┬──────┬──────────────┘
     │      │      │
     ▼      ▼      ▼
  사내 DB  GA4   Amplitude
(PostgreSQL/ (Google  (REST API /
 MySQL /    Analytics  SDK)
 BigQuery)  Data API)

────────────── 보안 경계 ──────────────
  위 모든 통신은 회사 네트워크 내부
  LLM 클라이언트에는 쿼리 결과(텍스트)만 전달
  원본 DB 자격증명은 서버 밖으로 나가지 않음
```

### MCP 서버 구조

MCP(Model Context Protocol)는 LLM 클라이언트와 외부 도구 서버 간의 표준 통신 규약이다. bi-agent는 이 규약을 구현한 FastMCP 프레임워크를 사용한다.

```
LLM 클라이언트                    bi-agent MCP 서버
─────────────                    ─────────────────
"이 테이블 스키마 보여줘"
        │
        ▼
[tools/list 요청]    ──────────▶  사용 가능한 tool 목록 반환
        │
[tools/call 요청]    ──────────▶  get_schema("orders") 실행
get_schema("orders")              └─▶ DB 쿼리 실행
                                      └─▶ 결과 텍스트 반환
        │             ◀──────────  스키마 정보 (텍스트)
        ▼
 "orders 테이블은 다음 컬럼을..."
```

통신 방식: **stdio** (표준 입출력). 별도 포트 개방 없이 로컬 프로세스 간 통신한다.

### 컴포넌트 구성도

```
bi_agent_mcp/
├── server.py          ── FastMCP 인스턴스 생성, tool 등록, 서버 실행
│
├── tools/
│   ├── db.py          ── DB 연결 등록, 스키마 조회, 쿼리 실행, 프로파일링
│   ├── ga4.py         ── Google Analytics 4 연동 (OAuth)
│   ├── amplitude.py   ── Amplitude 이벤트 데이터 조회
│   ├── tableau.py     ── TWBX 파일 초안 생성
│   └── analysis.py    ── 분석 방향 제안
│
├── auth/
│   ├── oauth.py       ── Google OAuth 2.0 PKCE 흐름
│   └── credentials.py ── 자격증명 저장·조회 (OS 키체인 / 환경변수)
│
└── config.py          ── 서버 설정, 상수 정의
```

### 데이터 흐름: 쿼리 실행 시

```
1. 사용자: "지난 7일 일별 주문 수 보여줘"
2. LLM: run_query("conn_prod", "SELECT date, COUNT(*) FROM orders ...") 호출
3. bi-agent:
   a. connection_id로 DB 자격증명 조회 (로컬 키체인/환경변수)
   b. SELECT 여부 검증 (DML 차단)
   c. LIMIT 500 강제 적용
   d. DB에 쿼리 전송
   e. 결과 rows를 마크다운 테이블 텍스트로 변환
4. LLM: 텍스트 결과를 받아 분석 코멘트 생성
5. 사용자: 마크다운 테이블 + 분석 코멘트 확인

※ 쿼리 결과 원본(rows)은 MCP 서버 메모리에서 즉시 소멸
※ LLM으로는 텍스트 표현만 전달
```

### 데이터 흐름: OAuth 인증 시 (GA4)

```
1. 사용자: connect_ga4("123456789") 호출
2. bi-agent:
   a. Google OAuth 2.0 PKCE 흐름 시작
   b. 로컬 브라우저에서 consent 페이지 열기
   c. 리다이렉트로 authorization code 수신 (localhost callback)
   d. code를 access_token + refresh_token으로 교환
   e. refresh_token을 OS 키체인에 저장
3. 이후 GA4 API 호출 시 저장된 token 자동 사용

※ 토큰은 로컬 OS 키체인에만 저장
※ MCP 서버 밖으로 token이 전송되지 않음
```

### 보안 경계

```
┌──────────────────────────────────────────────────────┐
│  회사 네트워크 / 로컬 머신                              │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  bi-agent MCP 서버 (신뢰 영역)               │    │
│  │  - DB 자격증명 보관                           │    │
│  │  - OAuth token 보관                          │    │
│  │  - 쿼리 실행                                  │    │
│  └─────────────────────────────────────────────┘    │
│          │ 텍스트(마크다운)만 통과                      │
│  ┌───────▼─────────────────────────────────────┐    │
│  │  LLM 클라이언트 컨텍스트 (반신뢰 영역)         │    │
│  │  - 쿼리 결과 텍스트 수신                       │    │
│  │  - 자격증명 접근 불가                          │    │
│  └─────────────────────────────────────────────┘    │
│          │ 자연어(프롬프트+결과)만 전송                  │
└──────────┼───────────────────────────────────────────┘
           │
    ┌──────▼──────┐
    │  LLM API    │  ← Anthropic / OpenAI / Google (외부)
    │  (외부 영역) │    여기에는 텍스트만 도달, 원본 데이터 없음
    └─────────────┘
```

---

## 3. MCP Tool 명세

### v0 — 핵심 DB 연결 (1주일)

#### `connect_db`

DB 연결 정보를 등록한다. 자격증명은 메모리에 보관하며 서버 재시작 시 사라진다. 영구 보관이 필요하면 환경 변수를 사용한다.

| 파라미터   | 타입    | 필수 | 설명                                       |
| ---------- | ------- | ---- | ------------------------------------------ |
| `type`     | string  | Y    | DB 종류: `postgresql`, `mysql`, `bigquery` |
| `host`     | string  | Y    | DB 호스트 주소                             |
| `port`     | integer | N    | 포트 (기본값: postgresql=5432, mysql=3306) |
| `database` | string  | Y    | 데이터베이스(스키마) 이름                  |
| `user`     | string  | Y    | 접속 계정                                  |
| `password` | string  | Y    | 비밀번호 (평문 전달 후 메모리 보관)        |

**출력 형식**
```
연결 등록 완료: conn_abc123
  유형: postgresql
  호스트: db.company.com:5432
  데이터베이스: analytics
```

**에러 처리**
- 접속 실패 시: `[ERROR] DB 연결 실패: {상세 오류}` 반환
- 지원하지 않는 DB 타입: `[ERROR] 지원하지 않는 DB 유형: {type}`

---

#### `list_connections`

등록된 DB 연결 목록을 반환한다. 비밀번호는 마스킹된다.

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| (없음)   | -    | -    | -    |

**출력 형식**
```
등록된 연결 목록 (2개):
- conn_abc123: analytics (postgresql) @ db.company.com:5432
- conn_def456: marketing  (mysql)      @ mysql.company.com:3306
```

---

#### `get_schema`

테이블 구조(컬럼명, 타입, PK, NOT NULL 여부, 행 수, 샘플 데이터)를 반환한다.

| 파라미터        | 타입   | 필수 | 설명                                         |
| --------------- | ------ | ---- | -------------------------------------------- |
| `connection_id` | string | Y    | `connect_db`로 등록한 연결 ID                |
| `table_name`    | string | N    | 특정 테이블명. 생략 시 전체 테이블 목록 반환 |

**출력 형식**
```
[스키마] analytics / orders (42,891행)

컬럼:
- order_id    : INTEGER  [PK, NOT NULL]
- user_id     : INTEGER  [NOT NULL]
- amount      : NUMERIC
- created_at  : TIMESTAMP

샘플 (2행):
  order_id=1001 | user_id=55 | amount=29000 | created_at=2024-01-15
  order_id=1002 | user_id=83 | amount=15000 | created_at=2024-01-15
```

**에러 처리**
- 존재하지 않는 연결 ID: `[ERROR] 연결을 찾을 수 없습니다: {connection_id}`
- 존재하지 않는 테이블: `테이블 '{table_name}'이 없습니다. 존재하는 테이블: ...`

---

#### `run_query`

SELECT 쿼리를 실행하고 결과를 마크다운 테이블로 반환한다.

| 파라미터        | 타입   | 필수 | 설명               |
| --------------- | ------ | ---- | ------------------ |
| `connection_id` | string | Y    | 등록된 연결 ID     |
| `sql`           | string | Y    | 실행할 SELECT 쿼리 |

**안전장치**
- SELECT로 시작하지 않으면 즉시 거부
- DROP, DELETE, INSERT, UPDATE, ALTER, CREATE 키워드 포함 시 거부
- 결과 행 수 최대 500행으로 자동 제한 (`LIMIT 500` 강제 적용)

**출력 형식**
```
**127건 반환** (SQL: `SELECT date, COUNT(*) FROM orders GROUP BY date`)

| date       | count |
| ---------- | ----- |
| 2024-01-15 | 342   |
| 2024-01-14 | 287   |
...
(총 127건 중 127건 표시)
```

**에러 처리**
- DML 감지: `보안 위반: SELECT 쿼리만 실행할 수 있습니다.`
- 쿼리 오류: `[ERROR] 쿼리 실행 오류: {DB 오류 메시지}`

---

#### `profile_table`

테이블의 각 컬럼에 대해 NULL 비율, 유니크 수, 최솟값/최댓값, 상위 5개 값을 계산한다.

| 파라미터        | 타입   | 필수 | 설명                  |
| --------------- | ------ | ---- | --------------------- |
| `connection_id` | string | Y    | 등록된 연결 ID        |
| `table_name`    | string | Y    | 프로파일링할 테이블명 |

**출력 형식**
```
[프로파일] orders (42,891행)

컬럼별 요약:
- order_id   : NULL 0.0% | 유니크 42,891 | MIN 1001 | MAX 44891
- user_id    : NULL 0.0% | 유니크 8,421
- amount     : NULL 1.2% | MIN 1000 | MAX 990000 | AVG 48,230
- created_at : NULL 0.0% | MIN 2023-01-01 | MAX 2024-03-15
- status     : NULL 0.0% | 유니크 4
  상위 5개: completed(68%), pending(18%), cancelled(11%), refunded(3%)
```

---

### v1 — 외부 데이터 소스 연동 (3-5일 추가)

#### `connect_ga4`

Google OAuth 2.0으로 GA4 속성에 연결한다. 브라우저가 열려 Google 계정 인증을 요청한다.

| 파라미터      | 타입   | 필수 | 설명                          |
| ------------- | ------ | ---- | ----------------------------- |
| `property_id` | string | Y    | GA4 속성 ID (예: `123456789`) |

**출력 형식**
```
GA4 연결 완료: ga4_123456789
  속성: My App (123456789)
  계정: analyst@company.com
  토큰 저장 위치: OS 키체인
```

---

#### `get_ga4_report`

GA4 Data API로 지표 데이터를 조회한다.

| 파라미터      | 타입         | 필수 | 설명                                           |
| ------------- | ------------ | ---- | ---------------------------------------------- |
| `property_id` | string       | Y    | GA4 속성 ID                                    |
| `metrics`     | list[string] | Y    | 지표 목록 (예: `["sessions", "activeUsers"]`)  |
| `dimensions`  | list[string] | N    | 차원 목록 (예: `["date", "country"]`)          |
| `date_range`  | object       | Y    | `{"start": "2024-01-01", "end": "2024-01-31"}` |

**출력 형식**
```
**GA4 리포트** (2024-01-01 ~ 2024-01-31)

| date       | sessions | activeUsers |
| ---------- | -------- | ----------- |
| 2024-01-15 | 12,340   | 8,921       |
...
```

---

#### `connect_amplitude`

Amplitude 프로젝트에 연결한다.

| 파라미터     | 타입   | 필수 | 설명                 |
| ------------ | ------ | ---- | -------------------- |
| `api_key`    | string | Y    | Amplitude API Key    |
| `secret_key` | string | Y    | Amplitude Secret Key |

---

#### `get_amplitude_events`

Amplitude 이벤트 데이터를 조회한다.

| 파라미터     | 타입   | 필수 | 설명                                           |
| ------------ | ------ | ---- | ---------------------------------------------- |
| `event_name` | string | Y    | 이벤트명 (예: `purchase_complete`)             |
| `date_range` | object | Y    | `{"start": "2024-01-01", "end": "2024-01-31"}` |
| `filters`    | object | N    | 필터 조건 (예: `{"country": "KR"}`)            |

---

#### `suggest_analysis`

현재 데이터 컨텍스트와 질문을 바탕으로 분석 방향을 제안한다. 실제 쿼리는 실행하지 않고 접근법과 지표를 안내한다.

| 파라미터       | 타입   | 필수 | 설명                                 |
| -------------- | ------ | ---- | ------------------------------------ |
| `data_context` | string | Y    | 데이터 설명 (스키마 요약, 도메인 등) |
| `question`     | string | Y    | 분석하고 싶은 비즈니스 질문          |

**출력 형식**
```
[분석 제안] "월별 이탈 고객 추세 파악"

권장 접근법:
1. 정의: 3개월 이상 구매 없는 고객 = 이탈
2. 지표: 월별 이탈 수, 이탈률(%), 평균 이탈 전 구매 횟수
3. 비교: 코호트별 이탈 패턴 비교
4. 다음 단계 쿼리 초안: ...
```

---

### v2 — 아웃풋 생성 (3-5일 추가)

#### `generate_twbx`

쿼리 결과와 차트 설정을 받아 Tableau 워크북 초안(.twbx)을 생성한다.

| 파라미터       | 타입   | 필수 | 설명                                        |
| -------------- | ------ | ---- | ------------------------------------------- |
| `query_result` | string | Y    | `run_query` 반환값 (마크다운 테이블 텍스트) |
| `chart_type`   | string | Y    | `bar`, `line`, `scatter`, `heatmap` 중 하나 |
| `title`        | string | Y    | 워크북/시트 제목                            |

**출력 형식**
```
TWBX 초안 생성 완료: ~/Downloads/월별_주문_추세.twbx
  차트 유형: line
  시트: 1개
  데이터 행: 31개

※ Tableau Desktop 또는 Tableau Public에서 열어 확인하세요.
※ 이 파일은 초안입니다. 색상·레이아웃은 직접 수정이 필요합니다.
```

---

#### `generate_report`

분석 섹션들을 조합해 마크다운 보고서 초안을 생성한다.

| 파라미터   | 타입         | 필수 | 설명                                                       |
| ---------- | ------------ | ---- | ---------------------------------------------------------- |
| `sections` | list[object] | Y    | `[{"title": "...", "content": "...", "data": "..."}]` 형식 |

---

#### `save_query`

자주 사용하는 쿼리를 이름으로 저장한다.

| 파라미터        | 타입   | 필수 | 설명                                |
| --------------- | ------ | ---- | ----------------------------------- |
| `name`          | string | Y    | 쿼리 식별 이름 (예: `daily_orders`) |
| `sql`           | string | Y    | 저장할 SQL                          |
| `connection_id` | string | Y    | 이 쿼리가 실행될 연결 ID            |

---

#### `list_saved_queries`

저장된 쿼리 목록을 반환한다.

| 파라미터 | 타입 | 필수 | 설명 |
| -------- | ---- | ---- | ---- |
| (없음)   | -    | -    | -    |

**출력 형식**
```
저장된 쿼리 (3개):
- daily_orders   (conn_abc123): SELECT date, COUNT(*) FROM orders...
- monthly_ltv    (conn_abc123): SELECT user_id, SUM(amount)...
- ga4_weekly     (ga4_123456): — GA4 쿼리 —
```

---

## 4. 인증 & 자격증명 관리

### 인증 방식별 처리

| 데이터 소스        | 인증 방식                            | 자격증명 보관 위치            | 갱신 방법               |
| ------------------ | ------------------------------------ | ----------------------------- | ----------------------- |
| PostgreSQL / MySQL | 직접 연결 (user/password)            | 환경 변수 또는 메모리         | 수동 재설정             |
| BigQuery           | Google OAuth 2.0 또는 서비스 계정 키 | OS 키체인 또는 JSON 파일 경로 | refresh_token 자동 갱신 |
| GA4                | Google OAuth 2.0 PKCE                | OS 키체인                     | refresh_token 자동 갱신 |
| Amplitude          | API Key + Secret Key                 | 환경 변수                     | 수동 재설정             |

### 자격증명 저장 우선순위

```
우선순위 1: 환경 변수 (권장)
  예: BI_AGENT_PG_PASSWORD=xxx

우선순위 2: OS 키체인 (OAuth token)
  macOS: Keychain Access
  Linux: libsecret (GNOME Keyring)
  Windows: Windows Credential Manager

우선순위 3: MCP 클라이언트 설정 파일 env 섹션
  (claude_desktop_config.json의 env 블록)

절대 사용 금지: 소스 코드에 평문 하드코딩
```

### 보안 원칙

- 비밀번호·토큰을 로그에 출력하지 않는다.
- `connect_db` 호출 시 password 파라미터는 메모리에서만 사용하며 디스크에 쓰지 않는다.
- `list_connections` 응답에서 password는 `****`로 마스킹한다.
- OAuth refresh_token은 OS 키체인에만 저장한다.

### 비전문가 온보딩 흐름

IT 비전문가(마케터 등)가 처음 설정할 때 LLM이 단계별로 안내하는 흐름이다.

```
사용자: "GA4 데이터 보고 싶어"
LLM:
  1단계: "GA4 속성 ID를 알려주세요.
          GA4 관리자 → 속성 → 속성 세부정보에서 확인할 수 있어요."
  2단계: connect_ga4("123456789") 호출
  → 브라우저 자동 열림 → Google 로그인 → 권한 허용
  3단계: "연결 완료! 어떤 데이터를 보시겠어요?"
```

DB 연결의 경우 LLM이 다음을 안내한다:
- 호스트/포트/DB명 확인 방법 (DBA에게 문의 또는 설정 파일 위치)
- 읽기 전용 계정 생성 권고 (`GRANT SELECT ON ALL TABLES TO bi_agent_user`)

---

## 5. 설치 & 배포

### 사용자 설치 방법

```bash
pip install bi-agent-mcp
```

Python 3.11 이상 필요. 가상환경 사용 권장:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install bi-agent-mcp
```

### Claude Desktop 설정

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_PORT": "5432",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "bi_agent_user",
        "BI_AGENT_PG_PASSWORD": "your_password_here"
      }
    }
  }
}
```

### Cursor 설정

`.cursor/mcp.json` (프로젝트 루트 또는 `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_USER": "bi_agent_user",
        "BI_AGENT_PG_PASSWORD": "your_password_here",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
```

### VSCode Copilot 설정

`.vscode/mcp.json`:

```json
{
  "servers": {
    "bi-agent": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_USER": "bi_agent_user",
        "BI_AGENT_PG_PASSWORD": "your_password_here",
        "BI_AGENT_PG_DBNAME": "analytics"
      }
    }
  }
}
```

### 환경 변수 전체 목록

| 변수명                          | 설명                       | 기본값      |
| ------------------------------- | -------------------------- | ----------- |
| `BI_AGENT_PG_HOST`              | PostgreSQL 호스트          | `localhost` |
| `BI_AGENT_PG_PORT`              | PostgreSQL 포트            | `5432`      |
| `BI_AGENT_PG_DBNAME`            | PostgreSQL 데이터베이스명  | -           |
| `BI_AGENT_PG_USER`              | PostgreSQL 사용자          | -           |
| `BI_AGENT_PG_PASSWORD`          | PostgreSQL 비밀번호        | -           |
| `BI_AGENT_MYSQL_HOST`           | MySQL 호스트               | `localhost` |
| `BI_AGENT_MYSQL_PORT`           | MySQL 포트                 | `3306`      |
| `BI_AGENT_MYSQL_DBNAME`         | MySQL 데이터베이스명       | -           |
| `BI_AGENT_MYSQL_USER`           | MySQL 사용자               | -           |
| `BI_AGENT_MYSQL_PASSWORD`       | MySQL 비밀번호             | -           |
| `BI_AGENT_AMPLITUDE_API_KEY`    | Amplitude API Key          | -           |
| `BI_AGENT_AMPLITUDE_SECRET_KEY` | Amplitude Secret Key       | -           |
| `BI_AGENT_QUERY_LIMIT`          | 쿼리 결과 최대 행 수       | `500`       |
| `BI_AGENT_GOOGLE_CLIENT_ID`     | Google OAuth Client ID     | -           |
| `BI_AGENT_GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | -           |

---

## 6. 데이터 보안

### 핵심 보안 원칙

```
[1] 데이터는 회사 인프라 밖으로 나가지 않는다
    - MCP 서버는 사용자 로컬 또는 사내 서버에서만 실행
    - LLM API로는 텍스트 표현만 전달 (원본 bytes 불전송)

[2] 읽기 전용 강제
    - SELECT 이외 모든 쿼리 차단
    - 위험 키워드(DROP, DELETE, INSERT 등) 탐지

[3] 결과 행 제한
    - 기본 500행 (BI_AGENT_QUERY_LIMIT 환경변수로 조정 가능)
    - 대량 데이터 실수 노출 방지

[4] 자격증명 보호
    - 평문 로그 기록 금지
    - 디스크 저장 시 OS 키체인 사용
    - 응답에서 비밀번호 마스킹
```

### SELECT 전용 강제 구현

```
쿼리 수신
    │
    ▼
[검사 1] query.strip().upper().startswith("SELECT")
    │ False → 즉시 거부 반환
    │ True
    ▼
[검사 2] 위험 키워드 포함 여부
  DROP / DELETE / INSERT / UPDATE / ALTER / CREATE / TRUNCATE
    │ 발견 → 즉시 거부 반환
    │ 없음
    ▼
[LIMIT 강제] SELECT * FROM ({원본 쿼리}) AS sub LIMIT 500
    │
    ▼
DB 실행 → 결과 반환
```

### 결과 row 제한 정책

| 상황                        | 제한 값                             | 이유                                |
| --------------------------- | ----------------------------------- | ----------------------------------- |
| 기본 설정                   | 500행                               | LLM 컨텍스트 크기 및 응답 지연 방지 |
| 프로파일링(`profile_table`) | 집계 쿼리만 실행, 원본 행 반환 없음 | 대용량 테이블 안전 처리             |
| 샘플 데이터(스키마 조회)    | 2행                                 | 참고용 최소 샘플                    |

### 데이터 로컬 캐싱 정책

- **기본: 캐시 없음.** 모든 쿼리는 매번 DB에 직접 실행된다.
- 쿼리 결과를 디스크에 저장하지 않는다.
- `save_query`는 SQL 텍스트만 저장하며 결과 데이터는 저장하지 않는다.

### 온프레미스 배포 시 LLM 격리 방안

인터넷 연결이 제한된 환경이나 데이터를 LLM API 외부로 전혀 보내고 싶지 않은 경우:

```
[Ollama + 로컬 LLM 구성]

사용자
  │
  ▼
Cursor / VSCode (LLM 클라이언트)
  │ localhost:11434 (Ollama API)
  ▼
Ollama (로컬 실행)
  - gemma3 / llama3 / mistral 등
  │ MCP stdio
  ▼
bi-agent MCP 서버 (로컬 실행)
  │
  ▼
사내 DB (네트워크 내부)

※ 이 구성에서는 모든 데이터가 로컬 머신 안에서만 처리됨
※ 인터넷 연결 불필요
```

---

## 7. 기존 코드 재사용 계획

### 재사용할 코드

| 기존 파일                                       | 재사용 방식                                                                             | 신규 위치                       |
| ----------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------- |
| `postgres_mcp.py`                               | FastMCP 서버 구조 (`mcp = FastMCP(...)`, `@mcp.tool()` 패턴, SELECT 안전장치 로직) 참조 | `bi_agent_mcp/server.py`        |
| `backend/agents/bi_tool/tableau_metadata.py`    | `TableauMetadataEngine` 클래스 — .twb XML 파싱·수정 로직                                | `bi_agent_mcp/tools/tableau.py` |
| `backend/agents/bi_tool/tableau_meta_schema.py` | `TableauMetaSchemaEngine` — 메타 스키마 생성 로직                                       | `bi_agent_mcp/tools/tableau.py` |
| `backend/core/tools.py`                         | `query_database()` — SELECT 안전장치, 마크다운 테이블 포맷, LIMIT 강제 적용 로직        | `bi_agent_mcp/tools/db.py`      |
| `backend/core/tools.py`                         | `analyze_schema()` — 스키마 분석 로직 (컬럼 타입, 행 수, 샘플)                          | `bi_agent_mcp/tools/db.py`      |
| `backend/core/tools.py`                         | `list_connections()` — 연결 목록 조회 패턴                                              | `bi_agent_mcp/tools/db.py`      |

### 폐기(무시)할 코드

| 경로                                                        | 이유                                                                  |
| ----------------------------------------------------------- | --------------------------------------------------------------------- |
| `backend/cli/` 전체                                         | TUI/CLI 인터페이스. MCP 서버에는 불필요                               |
| `backend/aac/` 전체                                         | AAC(Autonomous Agent Controller) 오케스트레이션. MCP로 대체           |
| `backend/orchestrator/` 전체                                | LangGraph 기반 오케스트레이터. MCP로 대체                             |
| `backend/agents/bi_tool/chart_recommender.py` 제외한 나머지 | 기존 에이전트 로직. 필요 시 개별 tool로 포팅                          |
| `pyproject.toml` 의존성 대부분                              | textual, langgraph, langchain, flask, weasyprint 등 MCP 서버에 불필요 |

---

## 8. 버전별 로드맵

```
v0 ──── v1 ──── v2 ──── v3
1주    +1-2주  +1-2주  미래
```

### v0 — 핵심 DB 연결 (목표: 1주일)

**목표**: 사내 DB에 연결해서 스키마 파악 + 쿼리 실행이 되는 최소 동작 서버

| 항목      | 내용                                                                         |
| --------- | ---------------------------------------------------------------------------- |
| Tools     | `connect_db`, `list_connections`, `get_schema`, `run_query`, `profile_table` |
| DB 지원   | PostgreSQL, MySQL                                                            |
| 보안      | SELECT 전용, LIMIT 500                                                       |
| 설치      | `pip install bi-agent-mcp`, Claude Desktop 설정 문서                         |
| 검증 기준 | Claude Desktop에서 "orders 테이블 구조 보여줘" → 스키마 반환                 |

### v1 — 외부 데이터 소스 연동 (목표: +1-2주)

**목표**: GA4 + Amplitude 데이터를 사내 DB 데이터와 함께 조회

| 항목      | 내용                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------ |
| Tools     | `connect_ga4`, `get_ga4_report`, `connect_amplitude`, `get_amplitude_events`, `suggest_analysis` |
| 인증      | Google OAuth 2.0 PKCE, Amplitude API Key                                                         |
| 검증 기준 | "지난 30일 GA4 세션 수" → 날짜별 테이블 반환                                                     |

### v2 — 아웃풋 생성 (목표: +1-2주)

**목표**: 쿼리 결과에서 Tableau 초안과 보고서 초안을 자동 생성

| 항목      | 내용                                                                   |
| --------- | ---------------------------------------------------------------------- |
| Tools     | `generate_twbx`, `generate_report`, `save_query`, `list_saved_queries` |
| 출력      | .twbx 파일 (로컬 다운로드 폴더), 마크다운 .md 파일                     |
| 검증 기준 | "월별 매출 막대 차트 만들어줘" → .twbx 파일 생성 → Tableau에서 열림    |

### v3 — 팀 공유 (미래)

| 항목 | 내용                                               |
| ---- | -------------------------------------------------- |
| 계획 | 저장된 쿼리 템플릿 팀 공유, 분석 북마크, 권한 관리 |
| 전제 | v2 완료 후 사용자 피드백 수집 뒤 방향 결정         |

---

## 9. 기술 스택

### 핵심 의존성

| 패키지                  | 버전  | 용도                       |
| ----------------------- | ----- | -------------------------- |
| `fastmcp`               | >=1.0 | MCP 서버 프레임워크        |
| `psycopg2-binary`       | >=2.9 | PostgreSQL 드라이버        |
| `pymysql`               | >=1.1 | MySQL 드라이버             |
| `google-cloud-bigquery` | >=3.0 | BigQuery 드라이버          |
| `google-auth`           | >=2.0 | Google 인증                |
| `google-auth-oauthlib`  | >=1.0 | Google OAuth 2.0 흐름      |
| `defusedxml`            | >=0.7 | Tableau .twb XML 안전 파싱 |

### 내장 모듈 활용

| 모듈                    | 용도                                       |
| ----------------------- | ------------------------------------------ |
| `zipfile`               | .twbx 패키징 (표준 내장)                   |
| `xml.etree.ElementTree` | .twb XML 처리 (표준 내장, defusedxml 우선) |
| `sqlite3`               | SQLite 지원 (표준 내장)                    |
| `os`, `pathlib`         | 파일 경로 처리                             |

### Amplitude

REST API 직접 호출 (별도 SDK 없음). `httpx` 또는 표준 `urllib.request` 사용.

### 의존성 합계 목표

```
필수 (v0): fastmcp + psycopg2-binary + pymysql = 3개
v1 추가:   google-cloud-bigquery + google-auth + google-auth-oauthlib = +3개
v2 추가:   defusedxml = +1개
────────────────────────────────────────────────────
합계: 7개 (목표 10개 이하 달성)
```

---

## 10. 파일 구조

```
bi_agent_mcp/                  ← 패키지 루트
│
├── __init__.py                ← 버전 정보
├── server.py                  ← FastMCP 인스턴스, tool 등록, 서버 실행 진입점
├── config.py                  ← 환경 변수 로드, 상수 (QUERY_LIMIT=500 등)
│
├── tools/                     ← MCP tool 구현체
│   ├── __init__.py
│   ├── db.py                  ← connect_db, list_connections, get_schema,
│   │                             run_query, profile_table
│   ├── ga4.py                 ← connect_ga4, get_ga4_report
│   ├── amplitude.py           ← connect_amplitude, get_amplitude_events
│   ├── tableau.py             ← generate_twbx
│   │                             (TableauMetadataEngine, TableauMetaSchemaEngine 재사용)
│   └── analysis.py            ← suggest_analysis, generate_report,
│                                 save_query, list_saved_queries
│
└── auth/                      ← 인증 및 자격증명
    ├── __init__.py
    ├── oauth.py               ← Google OAuth 2.0 PKCE 흐름
    └── credentials.py         ← OS 키체인 저장·조회, 환경변수 우선 로직

pyproject.toml                 ← 패키지 메타데이터, 의존성
README.md                      ← 설치 및 빠른 시작 가이드
```

### server.py 구조 (개요)

```python
from fastmcp import FastMCP
from bi_agent_mcp.tools.db import connect_db, list_connections, get_schema, run_query, profile_table
# ... 기타 import

mcp = FastMCP("bi-agent")

mcp.tool()(connect_db)
mcp.tool()(list_connections)
mcp.tool()(get_schema)
mcp.tool()(run_query)
mcp.tool()(profile_table)
# v1, v2 tools는 버전별로 추가

if __name__ == "__main__":
    mcp.run()  # stdio 모드로 실행
```

`postgres_mcp.py`의 `FastMCP("...") → @mcp.tool() → mcp.run()` 패턴을 동일하게 따른다.

---

*이 문서는 구현 전 설계 초안이다. 실제 구현 중 발견된 제약이나 변경사항은 이 문서에 반영한다.*
