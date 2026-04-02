# bi_tool_guide() — 디자인 스펙

**작성일:** 2026-04-02  
**상태:** 확정 (사용자 승인)  
**목표:** BI 툴을 모르는 사용자도 원하는 시각화를 만들 수 있도록, 의도 + 데이터 구조 기반의 단계별 가이드를 제공한다.

---

## 1. 비전

> "BI 툴 사용법을 몰라도, 내가 원하는 차트가 무엇인지만 말하면 된다."

사용자가 "월별 매출 추이를 보고 싶다"처럼 의도를 말하면, 어떤 차트 타입이 적합한지 추천하고, 선택한 BI 툴에서 실제로 만드는 방법을 컬럼명까지 포함해 단계별로 안내한다.

---

## 2. 함수 시그니처

```python
def bi_tool_guide(
    intent: str,        # 필수. "월별 매출 추이를 보고 싶다"
    columns: str = "",  # 선택. "date, revenue, region" 또는 JSON 형태
    tool: str = "",     # 선택. "tableau" / "powerbi" / "quicksight" / "looker"
    situation: str = "" # 선택. "연결 오류", "필터 추가" 등 트러블슈팅 키워드
) -> str:
    """[Helper] BI 툴 시각화 가이드.

    tool 미지정 → 차트 타입 추천 + 4개 툴 비교
    tool 지정   → 해당 툴의 단계별 가이드 반환
    """
```

---

## 3. 두 가지 모드

### 모드 1: 추천 모드 (tool 생략)

**입력:** `intent`, `columns` (선택)

**반환 내용:**
1. 추천 차트 타입 + 선택 이유
2. 4개 툴 1줄 비교 요약
3. "툴을 선택하면 상세 단계를 안내합니다" 안내

**예시:**
```
intent="월별 매출 추이", columns="date, revenue"

→ 추천: 라인 차트
   이유: 시간 축 변화 추이를 보기에 가장 직관적입니다.

   툴별 특징:
   - Tableau: 드래그앤드롭으로 가장 빠르게 구성 가능
   - Power BI: Excel 경험자라면 친숙한 UI
   - QuickSight: AWS 데이터 소스 연동이 네이티브
   - Looker: 팀 공유 및 버전 관리 강점

   → tool="tableau" 등으로 호출하면 단계별 가이드를 드립니다.
```

---

### 모드 2: 가이드 모드 (tool 지정)

**입력:** `intent`, `tool`, `columns` (권장), `situation` (선택)

**반환 내용:**
- 컬럼명이 포함된 번호 순 단계별 가이드 (마크다운)
- situation 지정 시: 해당 상황 트러블슈팅 가이드 우선 반환

**예시:**
```
intent="월별 매출 추이", columns="date, revenue", tool="tableau"

→ ## Tableau — 라인 차트 (월별 매출 추이)

   1단계: 데이터 소스 연결
      - 상단 메뉴 Data > New Data Source 클릭
      - 연결된 DB 또는 파일 선택

   2단계: 필드 배치
      - date 필드를 Columns 선반으로 드래그
      - revenue 필드를 Rows 선반으로 드래그

   3단계: 날짜 집계 설정
      - Columns의 date 우클릭 > Month 선택

   4단계: 차트 타입 변경
      - 우측 Show Me 패널에서 라인 차트 선택

   5단계: 포맷 (선택)
      - 제목 더블클릭하여 편집
      - revenue 축 우클릭 > Format으로 단위 설정
```

---

## 4. 지원 범위

### 4-1. 지원 툴

| 툴 | 파라미터 값 |
|----|------------|
| Tableau Desktop/Online | `tableau` |
| Power BI Desktop/Service | `powerbi` |
| Amazon QuickSight | `quicksight` |
| Looker Studio (구 Data Studio) | `looker` |

### 4-2. 차트 타입 매핑 — 퍼지 매칭 + 폴백

알려진 키워드는 구체적인 차트 가이드로 매핑하고, **매핑 안 되면 툴별 범용 차트 생성 워크플로우로 폴백**한다. `[ERROR]`는 반환하지 않는다.

| 의도 키워드 | 매핑 차트 | 폴백 여부 |
|------------|----------|----------|
| 추이, 변화, 트렌드, 시계열 | 라인 차트 | — |
| 비교, 순위 | 바 차트 | — |
| 비율, 구성 | 파이 / 도넛 차트 | — |
| 상관관계 | 산점도 | — |
| 지역, 지도 | 지도 차트 | — |
| 퍼널, 전환, 이탈 | 퍼널 차트 | — |
| 코호트, 리텐션 | 히트맵 / 코호트 테이블 | — |
| KPI, 요약 | 스코어카드 | — |
| **매핑 안 됨** | **범용 차트 생성 워크플로우** | **폴백** |

폴백 반환 예시:
```
"워터폴 차트"에 대한 정확한 가이드는 없지만, Tableau에서 새 시각화를 만드는 일반적인 흐름을 안내합니다.
1단계: ...
```

### 4-3. 상황 매핑 — 퍼지 매칭 + 폴백

situation 키워드도 동일하게 퍼지 매칭 후 매핑 안 되면 해당 툴의 **범용 문제 해결 흐름** 반환.

| 상황 | 키워드 예시 |
|------|-----------|
| 연결/인증 오류 | "연결 오류", "인증 실패", "DB 연결" |
| 차트 타입 변경 | "차트 바꾸기", "그래프 변경" |
| 필터/파라미터 | "필터 추가", "파라미터 설정" |
| 날짜 집계 | "월별", "주별", "날짜 그룹" |
| 계산 필드 | "MoM", "성장률", "계산 컬럼", "누적합" |
| 퍼블리시/공유 | "배포", "공유", "publish" |
| **매핑 안 됨** | **범용 문제 해결 흐름** (공식 문서 링크 포함) |

---

## 5. 구현 구조

### 파일 레이아웃

```
bi_agent_mcp/tools/bi_tool_guide.py   # 신규 생성
bi_agent_mcp/server.py                # bi_tool_guide 등록 추가
tests/unit/test_bi_tool_guide.py      # 신규 생성
```

### 내부 구조 (bi_tool_guide.py)

```python
# 상수 딕셔너리
_CHART_KEYWORDS: dict[str, str]       # 키워드 → 차트 타입 매핑 (퍼지용)
_CHART_GUIDE_FALLBACK: dict[str, list] # tool → 범용 차트 생성 단계 (폴백)
_TOOL_DESCRIPTIONS: dict[str, str]    # 툴 → 1줄 설명
_CHART_GUIDE: dict[str, dict]         # tool → chart_type → 단계 리스트
_SITUATION_GUIDE: dict[str, dict]     # tool → situation → 단계 리스트
_SITUATION_FALLBACK: dict[str, list]  # tool → 범용 트러블슈팅 단계 (폴백)

# 헬퍼
def _detect_chart_type(intent: str) -> str | None  # None이면 폴백 사용
def _detect_situation(situation: str) -> str | None
def _format_steps(steps: list[str], columns_map: dict) -> str
def _recommend_mode(intent: str, columns: str) -> str
def _guide_mode(intent: str, columns: str, tool: str, situation: str) -> str

# 메인 함수 (MCP 등록)
def bi_tool_guide(intent, columns, tool, situation) -> str
```

### 에러 처리

차트/상황 미매핑은 에러가 아닌 폴백. 에러는 진짜 잘못된 입력만 해당.

```python
# 알 수 없는 툴 (tool이 지정됐지만 지원 목록 밖)
return "[ERROR] 지원하지 않는 툴입니다. tool은 tableau / powerbi / quicksight / looker 중 하나여야 합니다."

# intent 비어있음
return "[ERROR] intent는 필수 파라미터입니다."

# 차트/상황 매핑 안 됨 → 에러 아님, 폴백 반환
```

---

## 6. 테스트 계획

| 테스트 케이스 | 종류 |
|-------------|------|
| tool 없이 호출 → 추천 모드 실행 | 정상 |
| tool="tableau" + intent + columns → 단계 포함 반환 | 정상 |
| tool="powerbi" + situation="연결 오류" → 트러블슈팅 반환 | 정상 |
| tool="quicksight" → 가이드 반환 | 정상 |
| tool="looker" → 가이드 반환 | 정상 |
| tool="unknown" → `[ERROR]` 반환 | 에러 |
| intent="" → `[ERROR]` 반환 | 에러 |
| columns 있을 때 컬럼명이 가이드에 포함되는지 확인 | 정상 |

최소 2개/함수 (정상 + 에러) 원칙 준수. 목표 커버리지 90%+.

---

## 7. server.py 등록 패턴

```python
# bi_tool_guide — BI 툴 시각화 가이드 (추천 + 단계별 안내)
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide
mcp.tool()(bi_tool_guide)
```

---

## 8. 성공 기준

```
bi_tool_guide("월별 매출 추이를 보고싶다", columns="date, revenue", tool="tableau")
→ 컬럼명 포함 5단계 가이드 반환

bi_tool_guide("매출 추이를 보고싶다")
→ 라인 차트 추천 + 4개 툴 비교 반환

bi_tool_guide("연결 오류", tool="powerbi", situation="연결 오류")
→ Power BI 연결 트러블슈팅 단계 반환
```
