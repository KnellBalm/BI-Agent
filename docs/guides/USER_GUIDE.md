# BI-Agent 사용자 가이드 (V0.1.1)

BI-Agent는 자연어로 데이터 분석 의도를 설명하고, AI 에이전트들의 협업을 통해 인터랙티브한 BI 대시보드를 생성하는 **지능형 분석 워크스페이스**입니다.

---

## 🚀 기동 및 초기 설정

### 1. 프로그램 실행
```bash
# 가상환경 활성화 후
bi-agent

# 또는
python -c "from backend.cli.app import main; main()"
```

### 2. TUI 구조 (3-Panel Dashboard)

실행 시 터미널 전체가 대시보드 모드로 전환됩니다:

```
┌──────────────────────────────────────────┐
│      (◉)           BI-Agent v0.1.1       │
│     /   \          gemini-2.5-flash · OK  │ ← 고정 헤더
│   (◉)───(◉)        sample_db (sqlite)    │
│  Orchestrating Intelligence · ~/project   │
├──────────────────────────────────────────┤
│ ❯ /help                                  │
│ ── 기본 명령어 ──                          │ ← 스크롤 출력 영역
│ /help   도움말 표시                        │
│ ...                                       │
├──────────────────────────────────────────┤
│ ❯ _                                       │ ← 고정 입력창
└──────────────────────────────────────────┘
```

- **헤더**: 마스코트, 모델명, 인증 상태, 연결된 DB, 작업 경로 표시 (항상 고정)
- **출력 영역**: 명령어 결과가 표시되며, 스크롤 가능
- **입력창**: `❯` 프롬프트 (항상 하단 고정)

### 3. LLM 인증
```bash
❯ /setting login gemini    # OAuth 로그인
❯ /setting set api_key YOUR_KEY   # API 키 직접 설정
```

---

## 🛠️ 주요 명령어

### 기본 (System)

| 명령어            | 설명                                                         |
| ----------------- | ------------------------------------------------------------ |
| `/help`           | 전체 명령어 도움말                                           |
| `/status`         | 현재 에이전트 상태 상세 확인 (모델, DB, 프로젝트, 활성 분석) |
| `/clear`          | 출력 영역 초기화                                             |
| `/quit` / `/exit` | 종료                                                         |

### 데이터 연결 (Data)

| 명령어                   | 설명                    | 예시                              |
| ------------------------ | ----------------------- | --------------------------------- |
| `/connect <타입> <경로>` | 데이터 소스 연결        | `/connect sqlite ./data/sales.db` |
| `/list`                  | 연결된 데이터 소스 목록 | `/list`                           |

지원 타입: `sqlite`, `excel`, `pg` (PostgreSQL)

### 데이터 탐색 (Explore)

| 명령어                      | 설명                  | 예시                                         |
| --------------------------- | --------------------- | -------------------------------------------- |
| `/explore schema`           | 전체 테이블 목록      | `/explore schema`                            |
| `/explore schema <테이블>`  | 특정 테이블 컬럼 상세 | `/explore schema sales`                      |
| `/explore query <SQL>`      | SQL 쿼리 실행         | `/explore query SELECT * FROM sales LIMIT 5` |
| `/explore preview <테이블>` | 상위 10행 미리보기    | `/explore preview orders`                    |

### 프로젝트 관리 (Project)

| 명령어                | 설명                                |
| --------------------- | ----------------------------------- |
| `/project new <이름>` | 현재 디렉터리에 `.bi-project/` 생성 |
| `/project list`       | 프로젝트 파일 구조 표시             |
| `/project status`     | 현재 프로젝트 상태                  |

### 리포트 관리 (Report)

| 명령어                         | 설명                    |
| ------------------------------ | ----------------------- |
| `/report new <제목>`           | 새 마크다운 리포트 생성 |
| `/report list`                 | 리포트 목록             |
| `/report show <이름>`          | 리포트 내용 표시        |
| `/report edit <이름>`          | `$EDITOR`로 편집        |
| `/report append <이름> <내용>` | 리포트에 섹션 추가      |

### AI 분석

| 명령어                 | 설명                         |
| ---------------------- | ---------------------------- |
| `/thinking <아이디어>` | 마크다운 분석 계획 자동 생성 |
| `/run <plan.md>`       | 계획 실행                    |
| `/expert <질문>`       | 딥 분석                      |
| 평문 질문              | AI가 자동 응답               |

### ALIVE 분석 플로우

| 명령어                 | 설명                 |
| ---------------------- | -------------------- |
| `/analysis new <제목>` | 새 분석 세션 생성    |
| `/analysis run`        | BI-EXEC 블록 실행    |
| `/analysis next`       | 다음 스테이지로 이동 |
| `/analysis status`     | 분석 상태 확인       |
| `/analysis list`       | 분석 세션 목록       |

---

## 📊 기본 워크플로우

```
1. bi-agent 실행
2. /connect sqlite ./data/sales.db     ← 데이터 소스 연결
3. /explore schema                      ← 테이블 구조 확인
4. /explore preview sales               ← 데이터 미리보기
5. /project new 매출분석               ← 프로젝트 생성
6. /thinking 월별 매출 추이 분석        ← AI가 분석 계획 수립
7. /run plan.md                         ← 계획 실행
8. /report show result                  ← 결과 확인
```

---

## 💡 팁
- **자동완성**: 명령어 입력 중 `Tab` 키를 누르면 명령어가 자동 완성됩니다.
- **에러 복구**: 쿼리 실행 중 에러가 발생하면 AI가 스스로 수정(Self-healing)을 시도합니다.
- **상태 확인**: `/status` 명령으로 현재 연결 상태, 프로젝트, 분석 현황을 한눈에 확인할 수 있습니다.

---
**마지막 업데이트**: 2026-03-06
Copyright © 2026 BI-Agent Team. All rights reserved.
