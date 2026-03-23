<!--
  이 파일은 AI 분석 컨텍스트로 자동 참조됩니다.
  자주 사용하는 분석 패턴을 기록하세요.
-->

# 분석 패턴 라이브러리

> `/bi-analyze` 스킬이 이 패턴들을 참조하여 최적의 분석 방법을 제안합니다.

## 📈 트렌드 분석

### 패턴: 월별 매출 트렌드
- **목적**: 매출 성장/하락 추세 파악
- **사용 테이블**: orders
- **예시 쿼리**:
```sql
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS order_count,
    SUM(amount) AS revenue,
    AVG(amount) AS aov
FROM orders
WHERE status = 'completed'
GROUP BY 1
ORDER BY 1;
```
- **해석 방법**: MoM 성장률 = (이번달 - 전달) / 전달 × 100

### 패턴: DAU/MAU 트렌드
- **목적**: 사용자 참여도 추세 파악
- **사용 테이블**: events 또는 sessions
- **예시 쿼리**:
```sql
-- [실제 이벤트 테이블명으로 수정]
SELECT
    DATE(created_at) AS date,
    COUNT(DISTINCT user_id) AS dau
FROM events
WHERE created_at >= NOW() - INTERVAL '90 days'
GROUP BY 1
ORDER BY 1;
```

## 🔍 코호트 분석

### 패턴: 월별 신규 가입자 코호트 리텐션
- **목적**: 신규 가입자의 재방문/재구매 패턴 파악
- **사용 테이블**: users, events
- **예시 쿼리**:
```sql
-- [실제 테이블/컬럼명으로 수정]
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('month', joined_at) AS cohort_month
    FROM users
)
SELECT
    c.cohort_month,
    DATE_TRUNC('month', e.created_at) AS activity_month,
    COUNT(DISTINCT e.user_id) AS active_users
FROM cohorts c
JOIN events e ON c.user_id = e.user_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

## 🎯 퍼널 분석

### 패턴: 구매 전환 퍼널
- **목적**: 방문→상품조회→장바구니→결제 전환율 분석
- **사용 테이블**: events
- **단계**: 방문(page_view) → 상품조회(view_item) → 장바구니(add_to_cart) → 결제(purchase)
- **예시 쿼리**:
```sql
-- [실제 이벤트명으로 수정]
SELECT
    event_name,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT user_id) * 100.0 / MAX(COUNT(DISTINCT user_id)) OVER() AS conversion_rate
FROM events
WHERE event_name IN ('page_view', 'view_item', 'add_to_cart', 'purchase')
    AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_name;
```

## 📊 세그먼트 분석

### 패턴: 고객 RFM 세그멘테이션
- **목적**: Recency/Frequency/Monetary 기반 고객 분류
- **사용 테이블**: orders
- **예시 쿼리**:
```sql
-- [실제 테이블/컬럼명으로 수정]
SELECT
    user_id,
    MAX(created_at) AS last_order_date,
    COUNT(*) AS order_count,
    SUM(amount) AS total_amount,
    DATEDIFF('day', MAX(created_at), NOW()) AS recency_days
FROM orders
WHERE status = 'completed'
GROUP BY user_id;
```

## 📝 사용자 정의 패턴

<!-- 자주 사용하는 분석 패턴을 여기에 추가하세요 -->

### 패턴: [패턴명]
- **목적**: [분석 목적]
- **사용 테이블**: [테이블명]
- **예시 쿼리**:
```sql
-- [쿼리 작성]
```
- **해석 방법**: [해석 가이드]
