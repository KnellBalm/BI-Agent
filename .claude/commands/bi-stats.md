# /bi-stats — 통계 분석 워크플로우

기술통계부터 가설검정까지 단계별 통계 분석을 수행합니다.
통계 지식이 없어도 결과를 쉽게 해석할 수 있도록 plain-language 판정을 제공합니다.

## 실행 절차

### 1단계: 데이터 파악

1. `list_connections`으로 연결 확인
2. $ARGUMENTS에서 분석할 테이블/컬럼 파악
   - 없으면: "어떤 데이터를 분석하시겠어요?" 질문
3. `descriptive_stats(conn_id, sql, columns=[...])` 실행
   - 평균, 표준편차, 최솟값, 최댓값, 분위수 확인

### 2단계: 분포 파악

4. `percentile_analysis(conn_id, sql, column)` — 백분위수 분포 확인
5. `boxplot_summary(conn_id, sql, column)` — IQR 및 이상치 개수 확인
6. `normality_test(conn_id, sql, column)` — 정규성 검정 (이후 검정 선택에 영향)

### 3단계: 가설검정 ($ARGUMENTS 또는 사용자 목적에 따라 선택)

**두 그룹 비교 시**:
- `ttest_independent(conn_id, sql, group_col, value_col)` — 독립 표본 t-검정

**전후 비교 시**:
- `ttest_paired(conn_id, sql, col_before, col_after)` — 대응 표본 t-검정

**3개 이상 그룹 비교 시**:
- `anova_one_way(conn_id, sql, group_col, value_col)` — 일원분산분석

**범주형 변수 관계 시**:
- `chi_square_test(conn_id, sql, col_a, col_b)` — 카이제곱 독립성 검정

**단일 집단 기준값 비교 시**:
- `ttest_one_sample(conn_id, sql, col, mu)` — 단일 표본 t-검정

### 4단계: 신뢰도 확인

7. `confidence_interval(conn_id, sql, column)` — 평균의 95% 신뢰구간
8. `sampling_error(conn_id, sql, column)` — 표본 오차 계산

## 검정 선택 가이드

| 목적 | 권장 검정 |
|------|---------|
| 두 그룹 평균 비교 | ttest_independent |
| 전후 효과 비교 | ttest_paired |
| 3개 이상 그룹 비교 | anova_one_way |
| 범주형 관계 확인 | chi_square_test |
| 기준값과 비교 | ttest_one_sample |
| 정규성 확인 | normality_test |

> p < 0.05 → 유의미한 차이 있음 (*), p < 0.01 → (**), p < 0.001 → (***)

## 출력 형식

```
## 통계 분석 결과: [데이터 설명]

### 기술 통계
[평균, 표준편차, 분위수 테이블]

### 분포 특성
[정규성 여부, 이상치 현황]

### 가설검정 결과
[검정명, 통계량, p값, 판정]

### 해석
[평이한 언어로 결과 설명 및 비즈니스 의미]
```

## 사용법

```
/bi-stats                              # 가이드 모드 (어떤 분석이 필요한지 파악)
/bi-stats 매출 데이터 기본 통계          # 기술통계 중심
/bi-stats A그룹 B그룹 평균 차이 비교     # 독립 t-검정
/bi-stats 지역별 구매금액 차이           # ANOVA
/bi-stats 성별과 구매여부 관계           # 카이제곱
```

## 사용 MCP 도구

- `descriptive_stats(conn_id, sql, columns)` — 기술 통계 (평균/표준편차/분위수)
- `percentile_analysis(conn_id, sql, col)` — 백분위수 분석
- `boxplot_summary(conn_id, sql, col, group_col)` — 박스플롯 요약 및 이상치
- `normality_test(conn_id, sql, col)` — 정규성 검정
- `ttest_one_sample(conn_id, sql, col, mu)` — 단일 표본 t-검정
- `ttest_independent(conn_id, sql, group_col, value_col)` — 독립 표본 t-검정
- `ttest_paired(conn_id, sql, col_before, col_after)` — 대응 표본 t-검정
- `anova_one_way(conn_id, sql, group_col, value_col)` — 일원분산분석
- `chi_square_test(conn_id, sql, col_a, col_b)` — 카이제곱 검정
- `confidence_interval(conn_id, sql, col)` — 신뢰구간
- `sampling_error(conn_id, sql, col)` — 표본 오차
- `hypothesis_helper(problem_type)` — 가설 설정 가이드
