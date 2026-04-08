# bi-history — 분석 히스토리 검색

과거 분석 세션을 검색하고 관리한다.
기본 검색은 LLM 없이 SQL 필터링만 사용한다. --deep 옵션이 있을 때만 LLM을 호출한다.

## 실행 규칙

1. 기본 검색은 LLM 없이 search_history() 하나로 완결한다
2. --deep 옵션이 명시된 경우에만 세션 파일을 읽고 LLM 분석을 수행한다
3. 결과에는 항상 세션 파일 경로(file_path)를 포함한다

---

## 실행 흐름

### $ARGUMENTS가 없는 경우 → 최근 목록

`search_history(limit=10)` 호출 → 최근 세션 10개 표시

### $ARGUMENTS가 있는 경우 (--deep 없음) → 키워드/필터 검색

`$ARGUMENTS`에서 다음을 파싱한다:
- `--type {값}`: 유형 필터 (diagnostic/exploratory/comparative/predictive/decision/monitoring)
- `--result {값}`: 결과 필터 (confirmed/rejected/inconclusive/in_progress)
- 위 플래그를 제외한 나머지 텍스트: query 검색어

`search_history(query=..., type=..., result=...)` 호출 → 결과 표시

### $ARGUMENTS + --deep → LLM 심층 검색

1. 위 방법으로 `search_history()`로 후보 추출
2. 결과의 각 `file_path`를 읽어 세션 내용 로드
3. LLM이 "가장 관련 있는 세션: ..." 형식으로 의미 기반 요약 제공

---

## 사용 예시

```
/bi-history                          → 최근 10개 세션 목록
/bi-history "매출"                   → 매출 관련 세션 검색
/bi-history --type diagnostic        → 진단형 전체 목록
/bi-history --result confirmed       → 가설 확인된 세션만
/bi-history "매출 광고" --deep       → LLM 심층 검색
```

## 사용 MCP 도구

- `search_history(query, type, result, limit)` — 히스토리 검색 (LLM 없음)
- `tag_session(session_id, add_tags)` — 기존 세션에 태그 추가
