<!--
  이 파일은 AI 분석 컨텍스트로 자동 참조됩니다.
  실제 데이터 소스 정보로 교체하세요.
-->

# 데이터 소스 정의

## 1. 운영 데이터베이스 (Primary DB)

**연결 방법**:
```
connect_db(
    db_type="postgresql",  # postgresql / mysql / snowflake / bigquery
    host="localhost",
    port=5432,
    database="[DB명]",
    user="[사용자명]"
)
```

### 주요 테이블 목록

| 테이블명 | 비즈니스 의미 | 주요 컬럼 | 업데이트 주기 |
|---------|-------------|---------|-------------|
| [테이블명] | [이 테이블이 나타내는 것] | [컬럼1, 컬럼2, ...] | [실시간/일별/월별] |
| [테이블명] | [이 테이블이 나타내는 것] | [컬럼1, 컬럼2, ...] | [실시간/일별/월별] |

<!-- 작성 예시 (이커머스):
| orders | 주문 정보 | order_id, user_id, amount, status, created_at | 실시간 |
| users | 회원 정보 | user_id, email, joined_at, plan_type | 실시간 |
| products | 상품 카탈로그 | product_id, name, category, price | 일별 |
| events | 사용자 행동 로그 | event_id, user_id, event_name, properties, occurred_at | 실시간 |
-->

### 테이블 관계 (ERD 개요)

<!-- 주요 테이블 간 관계를 기술하세요 -->
- `[테이블A]`.`[컬럼]` → `[테이블B]`.`[컬럼]` (관계 설명)

## 2. 분석 DB / 데이터 웨어하우스

<!-- BigQuery, Snowflake, Redshift 등 -->
- **플랫폼**: [없음 / BigQuery / Snowflake / Redshift]
- **주요 데이터셋**: [데이터셋명 및 용도]

## 3. Google Analytics 4 (GA4)

```
connect_ga4()  # 설정 필요: check_setup_status()로 확인
```

- **Property ID**: [GA4 Property ID]
- **주요 이벤트**: [purchase, sign_up, page_view 등]
- **주요 측정항목**: [sessions, conversions, revenue 등]

## 4. Amplitude

```
connect_amplitude()  # 설정 필요
```

- **Project**: [Amplitude 프로젝트명]
- **주요 이벤트**: [이벤트 목록]

## 5. 엑셀/CSV 파일

```
connect_file(path="[파일 경로]")
```

| 파일명 | 내용 | 업데이트 주기 | 담당자 |
|--------|------|-------------|--------|
| [파일명.xlsx] | [파일 내용] | [주기] | [담당자] |

## 6. 데이터 품질 메모

<!-- 알려진 데이터 품질 이슈를 기록하세요 -->
- [이슈 1]: [설명 및 처리 방법]
- [이슈 2]: [설명 및 처리 방법]
