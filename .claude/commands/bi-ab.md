# /bi-ab — A/B 테스트 전문 분석 워크플로우

A/B 테스트 설계부터 결과 해석까지 단계별로 안내합니다.
샘플 크기 계산 → 기본 검정 → 세그먼트 분석 → 시간 효과 확인까지 전 과정을 지원합니다.

## 실행 절차

### $ARGUMENTS가 "설계" 또는 "sample" 포함 시 → 실험 설계 모드

1. 사용자에게 다음 정보 확인:
   - 기준 전환율 (baseline_rate, 예: 0.05)
   - 목표 개선율 (mde, 예: 0.20 = 20% 상대 개선)
   - 유의수준 (alpha, 기본 0.05)
   - 검정력 (power, 기본 0.80)
2. `ab_sample_size(baseline_rate, mde, alpha, power)` 실행
3. 결과 해석: 그룹당 필요 샘플 수, 실험 기간 추정

### $ARGUMENTS가 "결과" 또는 "분석" 포함 시 → 결과 분석 모드

1. `list_connections`으로 연결된 DB 확인
2. 데이터 구조 파악 (group_col, metric_col 확인)
3. **기본 검정**: `ab_test_analysis(conn_id, sql, group_col, metric_col)` 실행
4. **다변형인 경우**: `ab_multivariate(conn_id, sql, group_col, metric_col)` 실행 (3개 이상 그룹)
5. **세그먼트 분석**: `ab_segment_breakdown(conn_id, sql, group_col, metric_col, segment_col)` 실행
   - device, region, user_type 등 주요 세그먼트 기준으로
6. **시간 효과 확인**: `ab_time_decay(conn_id, sql, group_col, metric_col, date_col)` 실행
   - Novelty Effect 경고 여부 확인
7. **신뢰구간 계산**: `confidence_interval(conn_id, sql, metric_col)` 각 그룹별 실행

### $ARGUMENTS 없을 시 → 가이드 모드

1. `hypothesis_helper(problem_type="ab_test", data_context="...")` 실행
2. 현재 단계 (설계/진행 중/분석) 질문 후 적합한 모드로 안내

## 출력 형식

```
## A/B 테스트 분석 결과

### 실험 요약
- 대조군(A): n=XXX, 전환율=X.XX%
- 실험군(B): n=XXX, 전환율=X.XX%
- Lift: +X.X%
- 통계적 유의성: [유의미한/유의미하지 않은] 차이 (p=X.XXX)

### 세그먼트별 효과 (있을 경우)
[세그먼트 분석 결과]

### Novelty Effect 판정 (있을 경우)
[시간적 효과 변화]

### 결론 및 권고
[통계 결과에 근거한 의사결정 가이드]
```

## 사용법

```
/bi-ab                          # 가이드 모드 (현재 단계 파악)
/bi-ab 설계 전환율 5% 개선목표 20%   # 실험 설계 모드
/bi-ab 결과 분석 users 테이블       # 결과 분석 모드
/bi-ab 샘플 크기 계산               # 샘플 계산 모드
```

## 사용 MCP 도구

- `ab_sample_size(baseline_rate, mde, alpha, power)` — 실험 설계: 필요 샘플 수
- `ab_test_analysis(conn_id, sql, group_col, metric_col)` — 기본 2그룹 비교
- `ab_multivariate(conn_id, sql, group_col, metric_col)` — A/B/C/n 다변형 비교
- `ab_segment_breakdown(conn_id, sql, group_col, metric_col, segment_col)` — 세그먼트별 효과
- `ab_time_decay(conn_id, sql, group_col, metric_col, date_col)` — Novelty Effect 감지
- `confidence_interval(conn_id, sql, col)` — 신뢰구간 계산
- `hypothesis_helper(problem_type="ab_test")` — 가설 설정 가이드
- `list_connections` — 연결된 DB 확인
