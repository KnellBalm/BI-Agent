> **새로운 분석을 시작한다면:** `/bi-solve` 를 먼저 사용하세요.
> bi-solve는 문제를 받아 분석 방향 설정부터 가설 검증까지 안내합니다.

# /bi-help — BI 분석 가이드 & 도구 선택

어디서 시작해야 할지 모를 때, 어떤 도구를 써야 할지 모를 때,
가설을 어떻게 세울지 모를 때 사용하는 종합 안내 스킬입니다.

## 실행 절차

### $ARGUMENTS가 있을 경우 → 맞춤 안내 모드

1. **도구 추천**: `bi_tool_selector(analysis_goal="$ARGUMENTS")` 실행
   - 98개 도구 중 목표에 맞는 핵심/보조 도구 + 워크플로우 제공
2. **분석 방법 추천**: `analysis_method_recommender(analysis_goal="$ARGUMENTS", data_types="...")` 실행
   - 분석 방법론 1/2/3순위 추천
3. 필요시: `hypothesis_helper(problem_type="...")` 실행
   - 가설 설정 → 검정 방법 → 결과 해석 단계별 가이드

### $ARGUMENTS가 없을 경우 → 탐색 모드

1. 사용자에게 3가지 선택지 제시:
   - "어떤 분석이 필요한지 알고 있어요" → $ARGUMENTS와 함께 재실행 안내
   - "어떤 분석을 해야 할지 모르겠어요" → `suggest_analysis` 실행
   - "데이터를 먼저 보고 싶어요" → `/bi-explore` 안내

2. **종합 도구 안내** 출력:

```
## BI-Agent 도구 카테고리 가이드

### 📊 시작하기
- /bi-connect — 데이터 소스 연결
- /bi-explore — 데이터 탐색 및 현황 파악

### 🔍 분석
- /bi-analyze — 도메인 기반 심층 분석
- /bi-stats  — 통계 분석 (t-검정, ANOVA, 카이제곱)
- /bi-ab     — A/B 테스트 설계 및 분석

### 📈 시각화 & 리포트
- /bi-viz    — 대시보드/Tableau 시각화
- /bi-report — 마크다운 분석 리포트

### ⚙️ 설정
- /bi-domain — 비즈니스 도메인 컨텍스트 설정
```

### $ARGUMENTS가 "가설" 포함 시 → 가설 검증 가이드

1. 어떤 문제인지 질문 (매출 감소? 전환율 하락? 그룹 차이?)
2. `hypothesis_helper(problem_type="...", data_context="...")` 실행
   - 귀무/대립가설 예시, 검정 방법, 전제 조건, 결과 해석 안내

### $ARGUMENTS가 "결과" 또는 "해석" 포함 시 → 결과 해석 모드

1. 쿼리 결과 정보 수집 (컬럼명, 행 수, 샘플 값)
2. `query_result_interpreter(columns=[...], row_count=N, sample_values=[...], question="...")` 실행
   - 결과 해석 방향, 후속 분석 제안

## 사용법

```
/bi-help                          # 종합 가이드 탐색 모드
/bi-help 매출 감소 원인 분석       # 매출 분석 도구 추천
/bi-help A/B 테스트 결과 해석      # A/B 도구 추천 + 가이드
/bi-help 가설 검증 방법            # 가설 설정 가이드
/bi-help 이 쿼리 결과 해석해줘     # 결과 해석 모드
/bi-help 고객 이탈 예측            # 이탈 분석 도구 추천
```

## 사용 MCP 도구

- `bi_tool_selector(analysis_goal, data_domain, constraints)` — 98개 도구 중 목표별 추천
- `analysis_method_recommender(analysis_goal, data_types, sample_size)` — 분석 방법론 추천
- `hypothesis_helper(problem_type, data_context, available_tables)` — 가설 검증 가이드
- `query_result_interpreter(columns, row_count, sample_values, question)` — 결과 해석
- `suggest_analysis(conn_id, table_name, question)` — 분석 방향 제안
- `list_connections` — 연결된 데이터 소스 확인
