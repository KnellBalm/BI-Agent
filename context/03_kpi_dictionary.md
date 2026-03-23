<!--
  이 파일은 AI 분석 컨텍스트로 자동 참조됩니다.
  실제 KPI 정의로 교체하세요. SQL은 실제 테이블명으로 수정하세요.
-->

# KPI / 지표 정의 사전

## 📊 매출 지표

| KPI명 | 정의 | 계산 방법 (SQL) | 목표값 | 담당자 |
|-------|------|----------------|--------|--------|
| 월 매출 (MRR) | 월간 반복 수익 | `SELECT SUM(amount) FROM orders WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())` | [목표] | [담당자] |
| 평균 주문 금액 (AOV) | 주문당 평균 금액 | `SELECT AVG(amount) FROM orders WHERE status = 'completed'` | [목표] | [담당자] |
| ARPU | 사용자당 평균 수익 | `SELECT SUM(amount) / COUNT(DISTINCT user_id) FROM orders` | [목표] | [담당자] |

<!-- 실제 KPI 추가 예시:
| LTV | 고객 생애 가치 | `SELECT AVG(total) FROM (SELECT user_id, SUM(amount) as total FROM orders GROUP BY user_id) t` | 150,000원 | 재무팀 |
-->

## 👥 사용자 지표

| KPI명 | 정의 | 계산 방법 (SQL) | 목표값 | 담당자 |
|-------|------|----------------|--------|--------|
| MAU | 월간 활성 사용자 | `SELECT COUNT(DISTINCT user_id) FROM events WHERE created_at >= NOW() - INTERVAL '30 days'` | [목표] | [담당자] |
| DAU | 일간 활성 사용자 | `SELECT COUNT(DISTINCT user_id) FROM events WHERE DATE(created_at) = CURRENT_DATE` | [목표] | [담당자] |
| 신규 가입자 | 이번 달 신규 가입 | `SELECT COUNT(*) FROM users WHERE DATE_TRUNC('month', joined_at) = DATE_TRUNC('month', NOW())` | [목표] | [담당자] |
| 이탈률 (Churn) | 월간 이탈 비율 | `[이탈 기준에 맞게 수정 필요]` | [목표] | [담당자] |

## 🔄 전환 지표

| KPI명 | 정의 | 계산 방법 (SQL) | 목표값 | 담당자 |
|-------|------|----------------|--------|--------|
| 구매 전환율 | 방문자 중 구매 비율 | `[GA4 데이터 필요]` | [목표] | [담당자] |
| 업셀 전환율 | 무료→유료 전환 비율 | `[플랜 전환 로직에 맞게 수정]` | [목표] | [담당자] |

## 📣 마케팅 지표

| KPI명 | 정의 | 계산 방법 (SQL) | 목표값 | 담당자 |
|-------|------|----------------|--------|--------|
| CAC | 고객 획득 비용 | `[마케팅 비용 / 신규 고객 수]` | [목표] | [담당자] |
| ROAS | 광고 수익률 | `[광고 수익 / 광고 비용 × 100]` | [목표] | [담당자] |

## ⚙️ 운영 지표

| KPI명 | 정의 | 계산 방법 (SQL) | 목표값 | 담당자 |
|-------|------|----------------|--------|--------|
| [지표명] | [정의] | [SQL] | [목표] | [담당자] |

## 📝 지표 해석 가이드

<!-- 지표 해석 시 주의사항 -->
- **[KPI명]**: [해석 시 주의사항, 정상 범위, 이상치 기준 등]
