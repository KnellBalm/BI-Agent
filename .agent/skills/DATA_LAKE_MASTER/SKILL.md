---
name: DATA_LAKE_MASTER
description: 데이터 소스(DB/Excel) 인프라 및 쿼리 최적화 전문가 스킬입니다.
---

# Data Lake Master 스킬 가이드

이 스킬은 시스템이 가용한 모든 데이터 자원을 식별하고, 최적의 경로로 데이터를 추출하며, 관리하는 지침을 제공합니다.

## 1. 핵심 책임
- **연결 매니지먼트**: `ConnectionManager`를 통한 DB/Excel/SaaS(Snowflake, BigQuery) 연결의 생명주기 관리.
- **SaaS & Cloud Analytics**: Snowflake, BigQuery 및 S3 파일 직접 질의를 위한 MCP 도구 활용 전략 수립.
- **쿼리 엔진 최적화**: 자연어를 SQL 또는 Pandas 쿼리로 변환할 때 효율성(인덱스 활용, 성능)과 보안을 담당합니다.
- **데이터 샘플링 & 요약**: 대용량 데이터 발생 시 컨텍스트 오버플로우를 방지하기 위한 Truncation 및 지능형 요약 전략을 수립합니다.

## 2. 세부 가이드라인

### [A] 데이터 소스 식별
- 사용자의 질문에서 '대상 데이터'가 명확하지 않을 경우, 메타데이터 조회를 통해 가장 관련성 높은 테이블/시트를 추천합니다.
- 연결되지 않은 외부 파일이나 DB 언급 시, 가상의 연결을 시도하기보다 `register_connection` 절차를 안내합니다.

### [B] 인텔리전트 쿼리
- **SQL**: 조인(Join) 보다는 필요한 컬럼만 명시적으로 가져오는 쿼리를 선호합니다.
- **Excel**: Pandas의 벡터 연산을 활용하도록 유도하며, 복잡한 필터링은 LLM 분석 단계(`_analyze_dataframe_with_llm`)로 위임합니다.

### [C] 데이터 보안 및 보존
- 민감한 설정값(Password 등)은 로그에 남기지 않으며, `connections.json`의 무결성을 유지합니다.

## 3. 액션 체크리스트
- [ ] 질문에 맞는 적절한 `connection_info`가 로드되었는가?
- [ ] 결과 데이터가 50행을 초과하여 Truncation이 필요한가?
- [ ] 쿼리 결과에 대한 일차적인 기술 통계(Count, Null count 등)를 제공할 수 있는가?
