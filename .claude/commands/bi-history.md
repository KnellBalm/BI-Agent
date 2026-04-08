# /bi-history — 분석 히스토리 검색

## 실행

이 스킬을 실행하기 전에 `skills/bi-history.md` 파일을 읽고 그 안의 지침을 정확히 따른다.

## 시작 방법

`$ARGUMENTS`가 없으면: `search_history(limit=10)`으로 최근 10개 표시
`$ARGUMENTS`가 있으면: 키워드/필터 파싱 후 `search_history()` 호출
`--deep` 플래그 있으면: 세션 파일 읽기 + LLM 심층 분석
