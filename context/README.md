# 비즈니스 도메인 지식 시스템 📚

> 이 디렉토리의 파일들은 AI 분석 시 자동으로 참조됩니다. 작성할수록 분석 품질이 향상됩니다.

## 목적

이 `context/` 디렉토리는 당신의 비즈니스 도메인 지식을 저장하는 공간입니다.
BI-Agent MCP 서버와 Claude Code 스킬이 이 파일들을 읽어 **도메인 맥락에 맞는 분석**을 제공합니다.

## 파일 구조

| 파일 | 내용 | 우선순위 |
|------|------|---------|
| [01_business_context.md](./01_business_context.md) | 회사/팀/사업 개요 | ⭐⭐⭐ 필수 |
| [02_data_sources.md](./02_data_sources.md) | 데이터 소스 및 테이블 설명 | ⭐⭐⭐ 필수 |
| [03_kpi_dictionary.md](./03_kpi_dictionary.md) | KPI 및 지표 정의 | ⭐⭐⭐ 필수 |
| [04_analysis_patterns.md](./04_analysis_patterns.md) | 자주 사용하는 분석 패턴 | ⭐⭐ 권장 |
| [05_glossary.md](./05_glossary.md) | 비즈니스 용어사전 | ⭐ 선택 |

## 사용 방법

### 1. 직접 참조
Claude Code에서 분석 요청 시 Claude가 자동으로 이 파일들을 읽습니다.

### 2. MCP 도구로 로드
```
load_domain_context(sections="all")        # 전체 컨텍스트 로드
load_domain_context(sections="kpis")       # KPI 정의만 로드
load_domain_context(sections="patterns")   # 분석 패턴만 로드
```

### 3. BI 스킬과 연동
```
/bi-analyze 이번 달 매출이 왜 감소했을까?   # 도메인 컨텍스트 자동 반영
/bi-explore orders                          # 테이블을 비즈니스 언어로 설명
/bi-report 월간 KPI 리포트                  # KPI 정의 기반 자동 리포트
/bi-domain                                  # 현재 도메인 설정 확인
```

## 작성 팁

1. **처음에는 01, 02, 03만 채워도 충분합니다**
2. 예시 내용(`<!-- 예시: ... -->`)을 지우고 실제 내용으로 교체하세요
3. SQL 쿼리는 실제 사용하는 테이블명/컬럼명으로 작성하세요
4. 정기적으로 업데이트하면 분석 품질이 지속적으로 향상됩니다

---
Copyright © 2026 BI-Agent Team
