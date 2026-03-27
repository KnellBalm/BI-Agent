"""BI/분석 가이드 도구 — 가설검증·분석방법론·결과해석·Tableau 시각화 헬퍼."""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def hypothesis_helper(
    problem_type: str,
    data_context: str = "",
    available_tables: str = "",
) -> str:
    """[Helper] 비즈니스 문제 유형별 가설 프레임워크와 검증 가이드를 제공합니다.

    suggest_analysis가 범용 분석 프레임워크를 제공하는 것과 달리,
    이 도구는 특정 문제 유형에 대해 구체적인 가설 목록과 각 가설을 검증할
    MCP 도구·SQL 패턴·해석 방법을 제공합니다.

    Args:
        problem_type: 문제 유형 (revenue_decline, churn_increase, conversion_drop,
                      user_growth, product_performance, marketing_effectiveness, general)
        data_context: 데이터 맥락 설명 (선택)
        available_tables: 사용 가능한 테이블 목록 (선택)

    Returns:
        가설 프레임워크 및 검증 가이드 (마크다운 문자열)
    """
    frameworks = {
        "revenue_decline": {
            "korean": "매출 하락",
            "hypotheses": [
                {
                    "title": "신규 고객 유입 감소",
                    "verify": "신규 고객 수와 기간별 추이를 분석합니다.",
                    "tools": "`growth_analysis`, `trend_analysis`",
                    "sql": "SELECT DATE_TRUNC('month', created_at) AS month, COUNT(*) AS new_customers\nFROM customers\nWHERE is_new = TRUE\nGROUP BY 1\nORDER BY 1",
                    "interpret": "결과가 하락세이면 마케팅 또는 유입 채널 문제를 의미합니다.",
                },
                {
                    "title": "기존 고객 구매 빈도 감소",
                    "verify": "기존 고객의 평균 구매 간격과 빈도 변화를 측정합니다.",
                    "tools": "`rfm_analysis`, `cohort_analysis`",
                    "sql": "SELECT customer_id, COUNT(*) AS purchase_count, AVG(amount) AS avg_amount\nFROM orders\nWHERE created_at >= CURRENT_DATE - INTERVAL '90 days'\nGROUP BY 1\nORDER BY 2 DESC",
                    "interpret": "구매 빈도 감소가 확인되면 재구매 유도 캠페인이 필요합니다.",
                },
                {
                    "title": "평균 주문 금액(AOV) 하락",
                    "verify": "기간별 평균 주문 금액 추이를 분석합니다.",
                    "tools": "`revenue_analysis`, `trend_analysis`",
                    "sql": "SELECT DATE_TRUNC('month', created_at) AS month,\n       AVG(amount) AS aov, SUM(amount) AS total_revenue\nFROM orders\nGROUP BY 1\nORDER BY 1",
                    "interpret": "AOV 하락은 고가 상품 판매 감소 또는 할인 남용을 의미할 수 있습니다.",
                },
                {
                    "title": "특정 카테고리/채널 집중 하락",
                    "verify": "카테고리 또는 채널별 매출 기여도 변화를 비교합니다.",
                    "tools": "`segment_analysis`, `revenue_analysis`",
                    "sql": "SELECT category, SUM(amount) AS revenue\nFROM orders\nGROUP BY 1\nORDER BY 2 DESC",
                    "interpret": "특정 카테고리 하락이면 해당 상품 경쟁력 또는 재고 문제를 점검하세요.",
                },
            ],
        },
        "churn_increase": {
            "korean": "이탈 증가",
            "hypotheses": [
                {
                    "title": "제품/서비스 품질 문제",
                    "verify": "이탈 시점 전후의 고객 불만 지표와 사용 패턴을 분석합니다.",
                    "tools": "`churn_analysis`, `anomaly_detection`",
                    "sql": "SELECT DATE_TRUNC('month', churned_at) AS month, COUNT(*) AS churned\nFROM churned_customers\nGROUP BY 1\nORDER BY 1",
                    "interpret": "이탈 급증 시점과 제품 변경 이력을 교차 확인하세요.",
                },
                {
                    "title": "경쟁사 대비 가격 경쟁력 하락",
                    "verify": "이탈 고객 세그먼트의 가격 민감도를 분석합니다.",
                    "tools": "`rfm_analysis`, `segment_analysis`",
                    "sql": "SELECT price_tier, COUNT(*) AS churn_count\nFROM churned_customers\nGROUP BY 1\nORDER BY 2 DESC",
                    "interpret": "저가 고객의 이탈이 높으면 가격 민감도 문제, 고가 고객이면 서비스 품질 문제입니다.",
                },
                {
                    "title": "온보딩/초기 경험 문제",
                    "verify": "가입 후 30일 이내 이탈률과 초기 활동 지표를 분석합니다.",
                    "tools": "`cohort_analysis`, `conversion_funnel`",
                    "sql": "SELECT DATEDIFF(churned_at, created_at) AS days_to_churn, COUNT(*) AS count\nFROM churned_customers\nGROUP BY 1\nORDER BY 1",
                    "interpret": "초기 이탈이 높으면 온보딩 경험 개선이 필요합니다.",
                },
                {
                    "title": "고객 지원/CS 불만족",
                    "verify": "CS 문의 빈도와 이탈 상관관계를 분석합니다.",
                    "tools": "`correlation_analysis`, `churn_analysis`",
                    "sql": "SELECT c.customer_id, COUNT(t.id) AS ticket_count, c.churned\nFROM customers c\nLEFT JOIN support_tickets t ON c.customer_id = t.customer_id\nGROUP BY 1, 3",
                    "interpret": "CS 문의가 많은 고객의 이탈률이 높으면 고객 지원 품질을 점검하세요.",
                },
            ],
        },
        "conversion_drop": {
            "korean": "전환율 하락",
            "hypotheses": [
                {
                    "title": "특정 퍼널 단계 이탈 증가",
                    "verify": "각 퍼널 단계별 전환율 변화를 시계열로 분석합니다.",
                    "tools": "`conversion_funnel`, `funnel_analysis`",
                    "sql": "SELECT step, COUNT(*) AS users, COUNT(*) * 100.0 / LAG(COUNT(*)) OVER (ORDER BY step_order) AS cvr\nFROM funnel_events\nGROUP BY 1, step_order\nORDER BY step_order",
                    "interpret": "이탈이 집중된 단계를 파악하고 UX 또는 콘텐츠를 개선하세요.",
                },
                {
                    "title": "트래픽 품질 변화",
                    "verify": "유입 채널별 전환율 차이를 비교합니다.",
                    "tools": "`segment_analysis`, `ab_test_analysis`",
                    "sql": "SELECT traffic_source, COUNT(*) AS sessions, SUM(converted) AS conversions,\n       SUM(converted) * 100.0 / COUNT(*) AS cvr\nFROM sessions\nGROUP BY 1\nORDER BY 4 DESC",
                    "interpret": "저품질 트래픽 채널 비중이 높아졌다면 마케팅 믹스를 조정하세요.",
                },
                {
                    "title": "랜딩 페이지 또는 UI 변경 영향",
                    "verify": "변경 전후 기간의 전환율을 A/B 비교합니다.",
                    "tools": "`ab_test_analysis`, `trend_analysis`",
                    "sql": "SELECT experiment_group, COUNT(*) AS users, SUM(converted) AS conversions,\n       SUM(converted) * 100.0 / COUNT(*) AS cvr\nFROM ab_test_events\nGROUP BY 1",
                    "interpret": "변경 후 전환율이 하락했다면 이전 버전으로 롤백을 고려하세요.",
                },
            ],
        },
        "user_growth": {
            "korean": "사용자 성장 분석",
            "hypotheses": [
                {
                    "title": "채널별 유입 성과 차이",
                    "verify": "채널별 신규 사용자 수와 CAC를 비교합니다.",
                    "tools": "`growth_analysis`, `segment_analysis`",
                    "sql": "SELECT acquisition_channel, COUNT(*) AS new_users,\n       SUM(cost) / COUNT(*) AS cac\nFROM user_acquisitions\nGROUP BY 1\nORDER BY 3",
                    "interpret": "CAC가 낮고 유입이 높은 채널에 투자를 집중하세요.",
                },
                {
                    "title": "바이럴/유기적 성장 기여도",
                    "verify": "유기적 유입과 유료 유입의 비율 추이를 분석합니다.",
                    "tools": "`trend_analysis`, `growth_analysis`",
                    "sql": "SELECT DATE_TRUNC('month', created_at) AS month,\n       SUM(CASE WHEN channel = 'organic' THEN 1 ELSE 0 END) AS organic,\n       SUM(CASE WHEN channel = 'paid' THEN 1 ELSE 0 END) AS paid\nFROM users\nGROUP BY 1\nORDER BY 1",
                    "interpret": "유기적 성장 비율이 높아지면 브랜드 인지도가 강화되고 있음을 의미합니다.",
                },
                {
                    "title": "지역/세그먼트별 성장 편차",
                    "verify": "지역 또는 세그먼트별 성장률 차이를 비교합니다.",
                    "tools": "`segment_analysis`, `cohort_analysis`",
                    "sql": "SELECT region, COUNT(*) AS users\nFROM users\nWHERE created_at >= CURRENT_DATE - INTERVAL '30 days'\nGROUP BY 1\nORDER BY 2 DESC",
                    "interpret": "특정 지역의 성장이 두드러지면 해당 지역 집중 투자를 검토하세요.",
                },
            ],
        },
        "product_performance": {
            "korean": "프로덕트 성과 분석",
            "hypotheses": [
                {
                    "title": "핵심 기능 사용률 저하",
                    "verify": "주요 기능별 사용 빈도와 사용자 수 추이를 분석합니다.",
                    "tools": "`trend_analysis`, `segment_analysis`",
                    "sql": "SELECT feature_name, COUNT(DISTINCT user_id) AS users,\n       COUNT(*) AS events\nFROM feature_events\nWHERE created_at >= CURRENT_DATE - INTERVAL '30 days'\nGROUP BY 1\nORDER BY 2 DESC",
                    "interpret": "핵심 기능 사용률 하락은 UX 문제 또는 기능 가치 저하를 의미합니다.",
                },
                {
                    "title": "사용자 활성도(DAU/MAU) 변화",
                    "verify": "일별/월별 활성 사용자 비율 추이를 분석합니다.",
                    "tools": "`growth_analysis`, `trend_analysis`",
                    "sql": "SELECT DATE_TRUNC('month', event_date) AS month,\n       COUNT(DISTINCT user_id) AS mau\nFROM events\nGROUP BY 1\nORDER BY 1",
                    "interpret": "DAU/MAU 비율 하락은 사용자 참여도 감소를 의미합니다.",
                },
                {
                    "title": "특정 사용자 세그먼트 이탈",
                    "verify": "세그먼트별 리텐션 차이를 코호트 분석으로 파악합니다.",
                    "tools": "`cohort_analysis`, `churn_analysis`",
                    "sql": "SELECT user_segment, retention_week, AVG(retention_rate) AS avg_retention\nFROM retention_cohorts\nGROUP BY 1, 2\nORDER BY 1, 2",
                    "interpret": "특정 세그먼트의 이탈이 높으면 맞춤형 개선 전략이 필요합니다.",
                },
            ],
        },
        "marketing_effectiveness": {
            "korean": "마케팅 효과성",
            "hypotheses": [
                {
                    "title": "채널별 ROI 차이",
                    "verify": "채널별 광고 비용 대비 매출 기여도를 비교합니다.",
                    "tools": "`revenue_analysis`, `segment_analysis`",
                    "sql": "SELECT channel, SUM(cost) AS spend, SUM(revenue) AS revenue,\n       SUM(revenue) / NULLIF(SUM(cost), 0) AS roas\nFROM marketing_campaigns\nGROUP BY 1\nORDER BY 4 DESC",
                    "interpret": "ROAS가 낮은 채널은 예산을 재배분하거나 캠페인을 최적화하세요.",
                },
                {
                    "title": "캠페인 타겟팅 효율성",
                    "verify": "타겟 세그먼트별 전환율과 CPA를 비교합니다.",
                    "tools": "`ab_test_analysis`, `segment_analysis`",
                    "sql": "SELECT target_segment, COUNT(*) AS impressions,\n       SUM(clicks) AS clicks, SUM(conversions) AS conversions,\n       SUM(cost) / NULLIF(SUM(conversions), 0) AS cpa\nFROM ad_campaigns\nGROUP BY 1\nORDER BY 5",
                    "interpret": "CPA가 낮은 세그먼트에 더 많은 예산을 할당하세요.",
                },
                {
                    "title": "마케팅 기여 어트리뷰션",
                    "verify": "멀티터치 어트리뷰션으로 각 채널의 실제 기여도를 측정합니다.",
                    "tools": "`conversion_funnel`, `revenue_analysis`",
                    "sql": "SELECT touchpoint_channel, COUNT(*) AS touches,\n       SUM(attributed_revenue) AS revenue\nFROM attribution_model\nGROUP BY 1\nORDER BY 3 DESC",
                    "interpret": "라스트 클릭이 아닌 멀티터치 기여도를 참고하여 예산 배분을 최적화하세요.",
                },
                {
                    "title": "시즌성/타이밍 효과",
                    "verify": "캠페인 집행 시기와 효과 간의 패턴을 분석합니다.",
                    "tools": "`trend_analysis`, `anomaly_detection`",
                    "sql": "SELECT DAYOFWEEK(campaign_date) AS day_of_week,\n       AVG(ctr) AS avg_ctr, AVG(conversion_rate) AS avg_cvr\nFROM campaign_daily_stats\nGROUP BY 1\nORDER BY 1",
                    "interpret": "특정 요일/시간대에 성과가 집중되면 캠페인 스케줄링을 최적화하세요.",
                },
            ],
        },
        "general": {
            "korean": "일반 비즈니스 분석",
            "hypotheses": [
                {
                    "title": "핵심 지표 추이 파악",
                    "verify": "주요 KPI의 시계열 변화를 분석합니다.",
                    "tools": "`trend_analysis`, `growth_analysis`",
                    "sql": "SELECT DATE_TRUNC('month', event_date) AS month,\n       COUNT(*) AS events, COUNT(DISTINCT user_id) AS users\nFROM events\nGROUP BY 1\nORDER BY 1",
                    "interpret": "추이가 상승이면 긍정적, 하락이면 원인 파악이 필요합니다.",
                },
                {
                    "title": "세그먼트 간 성과 차이",
                    "verify": "그룹/세그먼트별 핵심 지표 차이를 비교합니다.",
                    "tools": "`segment_analysis`, `ab_test_analysis`",
                    "sql": "SELECT segment, COUNT(*) AS users, AVG(metric_value) AS avg_metric\nFROM user_metrics\nGROUP BY 1\nORDER BY 3 DESC",
                    "interpret": "세그먼트 간 차이가 크면 맞춤형 전략이 효과적입니다.",
                },
                {
                    "title": "이상값/이상 패턴 감지",
                    "verify": "통계적 이상값과 비정상 패턴을 탐지합니다.",
                    "tools": "`anomaly_detection`, `distribution_analysis`",
                    "sql": "SELECT event_date, metric_value,\n       AVG(metric_value) OVER (ORDER BY event_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg\nFROM daily_metrics\nORDER BY event_date",
                    "interpret": "이동 평균 대비 급격한 변화가 있으면 원인을 조사하세요.",
                },
            ],
        },
    }

    normalized = problem_type.strip().lower()
    if normalized not in frameworks:
        logger.warning("지원하지 않는 problem_type '%s', general로 대체합니다.", problem_type)
        normalized = "general"

    fw = frameworks[normalized]
    lines = [f"## 가설 프레임워크: {fw['korean']}"]

    if data_context:
        lines.append(f"\n**데이터 맥락**: {data_context}")
    if available_tables:
        lines.append(f"**사용 가능한 테이블**: {available_tables}")

    lines.append("")

    for i, h in enumerate(fw["hypotheses"], 1):
        lines.append(f"### 가설 {i}: {h['title']}")
        lines.append(f"- **검증 방법**: {h['verify']}")
        lines.append(f"- **권장 도구**: {h['tools']}")
        lines.append(f"- **SQL 패턴**:\n```sql\n{h['sql']}\n```")
        lines.append(f"- **해석 가이드**: {h['interpret']}")
        lines.append("")

    return "\n".join(lines)


def analysis_method_recommender(
    analysis_goal: str,
    data_types: str = "",
    sample_size: int = 0,
) -> str:
    """[Helper] 분석 목적에 맞는 방법론과 MCP 도구를 추천합니다.

    suggest_analysis가 분석 절차 전체 프레임워크를 제공하는 것과 달리,
    이 도구는 특정 분석 목적(그룹 비교, 예측 등)에 맞는 방법론을 선택하고
    어떤 MCP 도구를 사용해야 하는지 안내합니다.

    Args:
        analysis_goal: 분석 목적 (자연어로 입력, 예: "두 그룹 간 차이 검정")
        data_types: 데이터 타입 설명 (선택, 예: "연속형, 범주형")
        sample_size: 샘플 크기 (선택, 0이면 미지정)

    Returns:
        추천 분석 방법론과 MCP 도구 안내 (마크다운 문자열)
    """
    goal_lower = analysis_goal.lower()

    recommendations = []

    if any(k in goal_lower for k in ["그룹 비교", "차이 검정", "비교 분석"]):
        recommendations.append({
            "method": "독립 표본 t-검정 / 분산 분석(ANOVA)",
            "tools": ["`ttest_independent`", "`anova_one_way`", "`ab_test_analysis`"],
            "when": "두 개 이상의 그룹 간 평균 차이를 통계적으로 검증할 때",
            "note": "정규성 가정 위반 시 Mann-Whitney U 검정 또는 Kruskal-Wallis 검정 사용을 권장합니다.",
        })

    if any(k in goal_lower for k in ["시계열", "트렌드", "월별", "추이", "시간"]):
        recommendations.append({
            "method": "시계열 분석 / 트렌드 분석",
            "tools": ["`trend_analysis`", "`moving_average_forecast`", "`growth_analysis`"],
            "when": "시간에 따른 지표 변화 패턴과 추세를 파악할 때",
            "note": "계절성이 있는 데이터는 분해(decomposition) 기법을 적용하세요.",
        })

    if any(k in goal_lower for k in ["상관관계", "관계", "연관", "영향"]):
        recommendations.append({
            "method": "상관 분석 / 카이제곱 검정",
            "tools": ["`correlation_analysis`", "`chi_square_test`"],
            "when": "두 변수 간 관계의 강도와 방향을 파악할 때",
            "note": "상관관계는 인과관계를 의미하지 않습니다. 교란 변수를 확인하세요.",
        })

    if any(k in goal_lower for k in ["분포", "히스토그램", "정규성"]):
        recommendations.append({
            "method": "분포 분석 / 정규성 검정",
            "tools": ["`distribution_analysis`", "`descriptive_stats`", "`normality_test`"],
            "when": "데이터의 분포 형태와 통계적 특성을 파악할 때",
            "note": "분포 확인은 후속 통계 검정 방법 선택에 필수적입니다.",
        })

    if any(k in goal_lower for k in ["예측", "포캐스팅", "forecast", "미래"]):
        recommendations.append({
            "method": "시계열 예측 / 회귀 예측",
            "tools": ["`linear_trend_forecast`", "`exponential_smoothing_forecast`"],
            "when": "과거 데이터를 기반으로 미래 값을 예측할 때",
            "note": "예측 모델의 신뢰 구간을 함께 확인하세요. 외삽 범위가 넓을수록 불확실성이 커집니다.",
        })

    if any(k in goal_lower for k in ["이탈", "churn", "탈퇴", "비활성"]):
        recommendations.append({
            "method": "이탈 분석 / RFM 분석",
            "tools": ["`churn_analysis`", "`rfm_analysis`"],
            "when": "고객 이탈 패턴 파악 및 이탈 위험 고객을 식별할 때",
            "note": "이탈 예측 모델 구축 시 생존 분석(survival analysis) 기법도 검토하세요.",
        })

    if any(k in goal_lower for k in ["퍼널", "전환", "funnel", "conversion"]):
        recommendations.append({
            "method": "퍼널 분석 / 전환율 분석",
            "tools": ["`conversion_funnel`", "`funnel_analysis`"],
            "when": "사용자가 목표에 도달하는 과정의 단계별 이탈률을 분석할 때",
            "note": "퍼널 단계 정의가 분석 결과에 큰 영향을 미칩니다. 명확히 정의하세요.",
        })

    if any(k in goal_lower for k in ["고객 세분화", "세그먼트", "클러스터", "분류"]):
        recommendations.append({
            "method": "세그먼트 분석 / RFM 분석 / 코호트 분석",
            "tools": ["`segment_analysis`", "`rfm_analysis`", "`cohort_analysis`"],
            "when": "고객을 유사한 특성으로 그룹화하고 그룹별 행동 패턴을 파악할 때",
            "note": "세그먼트 크기가 너무 작으면 통계적 유의성이 낮아질 수 있습니다.",
        })

    if not recommendations:
        recommendations.append({
            "method": "기술 통계 / 탐색적 데이터 분석(EDA)",
            "tools": ["`descriptive_stats`", "`distribution_analysis`", "`trend_analysis`"],
            "when": "분석 목적이 명확하지 않을 때 데이터의 전반적인 특성을 파악하는 첫 단계",
            "note": "EDA 후 구체적인 분석 방향이 정해지면 이 도구를 다시 호출하세요.",
        })

    lines = [f"## 분석 방법론 추천: {analysis_goal}", ""]

    if data_types:
        lines.append(f"**데이터 타입**: {data_types}")
    if sample_size > 0:
        size_note = "소규모 (비모수 검정 고려)" if sample_size < 30 else ("대규모 (중심극한정리 적용 가능)" if sample_size >= 1000 else "중규모")
        lines.append(f"**샘플 크기**: {sample_size:,}개 → {size_note}")
    lines.append("")

    for i, rec in enumerate(recommendations, 1):
        lines.append(f"### 추천 {i}: {rec['method']}")
        lines.append(f"- **권장 MCP 도구**: {', '.join(rec['tools'])}")
        lines.append(f"- **적용 시점**: {rec['when']}")
        lines.append(f"- **주의사항**: {rec['note']}")
        lines.append("")

    return "\n".join(lines)


def query_result_interpreter(
    columns: list,
    row_count: int,
    sample_values: str = "",
    question: str = "",
) -> str:
    """[Helper] 쿼리 결과를 해석하고 추가 분석 방향을 제안합니다.

    Args:
        columns: 컬럼명 목록
        row_count: 결과 행 수
        sample_values: 샘플 값 설명 (선택)
        question: 분석 질문 (선택)

    Returns:
        결과 해석 및 추가 분석 제안 (마크다운 문자열)
    """
    lines = ["## 쿼리 결과 해석", ""]

    # 데이터 개요
    lines.append("### 데이터 개요")
    lines.append(f"- **컬럼 수**: {len(columns)}개")
    lines.append(f"- **행 수**: {row_count:,}개")
    lines.append(f"- **컬럼 목록**: {', '.join(columns)}")

    # 컬럼 타입 추정
    date_keywords = ["date", "time", "month", "year", "day", "created", "updated", "at"]
    numeric_keywords = ["count", "sum", "total", "amount", "price", "revenue", "rate",
                        "avg", "mean", "cnt", "num", "qty", "value", "score"]
    id_keywords = ["id", "key", "code"]

    col_types = {}
    for col in columns:
        col_lower = col.lower()
        if any(k in col_lower for k in date_keywords):
            col_types[col] = "날짜/시간"
        elif any(k in col_lower for k in numeric_keywords):
            col_types[col] = "수치형"
        elif any(k in col_lower for k in id_keywords):
            col_types[col] = "식별자"
        else:
            col_types[col] = "범주형/기타"

    lines.append("\n**컬럼 타입 추정**:")
    for col, ctype in col_types.items():
        lines.append(f"  - `{col}`: {ctype}")

    if sample_values:
        lines.append(f"\n**샘플 값**: {sample_values}")

    lines.append("")

    # 결과 해석 포인트
    lines.append("### 결과 해석 포인트")

    if row_count == 0:
        lines.append("- **주의**: 결과가 없습니다. 다음 사항을 확인하세요:")
        lines.append("  - WHERE 조건이 너무 엄격하지 않은지 확인")
        lines.append("  - 날짜 범위가 올바른지 확인")
        lines.append("  - 테이블에 데이터가 실제로 존재하는지 확인")
    elif row_count < 10:
        lines.append(f"- 결과가 {row_count}개로 적습니다. 필터 조건을 완화하거나 데이터 수집 기간을 늘려보세요.")
    elif row_count > 100000:
        lines.append(f"- 결과가 {row_count:,}개로 많습니다. 집계 또는 샘플링을 적용하는 것을 권장합니다.")
    else:
        lines.append(f"- 총 {row_count:,}개의 레코드가 반환되었습니다.")

    if question:
        lines.append(f"- **분석 질문**: '{question}'에 대한 결과입니다.")

    # 컬럼 조합 기반 분석 방향 추론
    has_date = any(v == "날짜/시간" for v in col_types.values())
    has_numeric = any(v == "수치형" for v in col_types.values())
    has_category = any(v == "범주형/기타" for v in col_types.values())

    if has_date and has_numeric:
        lines.append("- 날짜 + 수치형 컬럼이 있어 **시계열 트렌드 분석**에 적합합니다.")
    if has_category and has_numeric:
        lines.append("- 범주형 + 수치형 컬럼이 있어 **그룹별 비교 분석**에 적합합니다.")

    lines.append("")

    # 추가 분석 제안
    lines.append("### 추가 분석 제안")

    suggested_tools = set()
    for col in columns:
        col_lower = col.lower()
        if any(k in col_lower for k in ["revenue", "amount", "sales", "매출"]):
            suggested_tools.add("`revenue_analysis`")
        if any(k in col_lower for k in ["churn", "churned", "이탈"]):
            suggested_tools.add("`churn_analysis`")
        if any(k in col_lower for k in ["date", "month", "time", "날짜"]):
            suggested_tools.add("`trend_analysis`")
        if any(k in col_lower for k in ["segment", "group", "category", "세그먼트"]):
            suggested_tools.add("`segment_analysis`")
        if any(k in col_lower for k in ["rate", "ratio", "pct", "percent", "비율"]):
            suggested_tools.add("`distribution_analysis`")

    if not suggested_tools:
        suggested_tools = {"`descriptive_stats`", "`distribution_analysis`"}

    lines.append(f"- 다음 MCP 도구를 활용한 심층 분석을 권장합니다: {', '.join(sorted(suggested_tools))}")

    if row_count > 0 and has_numeric:
        lines.append("- 수치형 컬럼의 이상값 탐지를 위해 `anomaly_detection`을 실행해보세요.")
    if has_date:
        lines.append("- 날짜 컬럼을 활용한 코호트 분석에 `cohort_analysis`를 고려하세요.")

    lines.append("")

    # 주의사항
    lines.append("### 주의사항")
    lines.append("- 이 해석은 컬럼명과 행 수 기반의 추정입니다. 실제 데이터 내용을 확인하여 검증하세요.")
    lines.append("- NULL 값이 많은 컬럼은 분석 결과를 왜곡할 수 있습니다. `SELECT COUNT(*) - COUNT(column_name)` 으로 NULL 수를 확인하세요.")
    lines.append("- 집계 쿼리의 경우 GROUP BY 기준과 집계 함수가 분석 목적에 맞는지 확인하세요.")

    return "\n".join(lines)


def tableau_viz_guide(
    chart_goal: str,
    data_columns: Optional[list] = None,
    detail_level: str = "basic",
) -> str:
    """[Helper] Tableau 시각화 step-by-step 가이드를 제공합니다.
    generate_twbx 도구로 실제 .twbx 파일을 생성할 수 있습니다.

    Args:
        chart_goal: 시각화 목표 (예: "월별 매출 트렌드", "카테고리 비교")
        data_columns: 사용할 컬럼 목록 (선택)
        detail_level: 상세 수준 ("basic" 또는 "advanced")

    Returns:
        Tableau 시각화 가이드 (마크다운 문자열)
    """
    goal_lower = chart_goal.lower()

    if any(k in goal_lower for k in ["트렌드", "시계열", "월별", "일별", "추이", "time"]):
        chart_config = {
            "chart_type": "line",
            "chart_name": "꺾은선형 차트 (Line Chart)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. 날짜 필드를 **Columns** 선반으로 드래그합니다.",
                "3. 측정값(매출, 사용자 수 등)을 **Rows** 선반으로 드래그합니다.",
                "4. 날짜 필드를 우클릭하여 원하는 단위(월, 주, 일)를 선택합니다.",
                "5. **Show Me** 패널에서 꺾은선형 차트를 클릭하여 적용합니다.",
            ],
            "advanced_steps": [
                "**LOD(Level of Detail) 계산식으로 동기간 비교:**",
                "```\n{ FIXED [Month] : SUM([Revenue]) }\n```",
                "**테이블 계산으로 전월 대비 증감률:**",
                "```\n(SUM([Revenue]) - LOOKUP(SUM([Revenue]), -1)) / ABS(LOOKUP(SUM([Revenue]), -1))\n```",
                "**필터 적용 순서**: 데이터 원본 필터 → 추출 필터 → 컨텍스트 필터 → 차원 필터 → 측정값 필터 순으로 적용됩니다.",
                "**Dual Axis**: 두 측정값을 비교할 때 두 번째 측정값을 Rows에 추가 후 우클릭 → Dual Axis를 선택합니다.",
                "**Trend Line**: Analytics 패널에서 Trend Line을 드래그하면 추세선을 추가할 수 있습니다.",
            ],
        }
    elif any(k in goal_lower for k in ["비교", "막대", "bar", "랭킹", "순위"]):
        chart_config = {
            "chart_type": "bar",
            "chart_name": "막대 차트 (Bar Chart)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. 범주형 필드를 **Rows** 선반으로 드래그합니다.",
                "3. 측정값을 **Columns** 선반으로 드래그합니다.",
                "4. **Show Me** 패널에서 막대 차트를 선택합니다.",
                "5. 측정값 축을 우클릭 → Sort 로 내림차순 정렬을 적용합니다.",
            ],
            "advanced_steps": [
                "**Top N 필터로 상위 항목만 표시:**",
                "범주 필드를 우클릭 → Filter → Top 탭에서 N 값을 설정합니다.",
                "**Reference Line으로 평균선 표시:**",
                "Analytics 패널에서 Reference Line을 Columns 축으로 드래그합니다.",
                "**Bar in Bar 차트 (비교용):**",
                "Size 마크를 조정하여 두 측정값의 막대를 겹쳐 표시할 수 있습니다.",
                "**필터 순서**: 컨텍스트 필터를 먼저 설정하면 Top N 필터가 정확하게 작동합니다.",
                "**색상 인코딩**: 범주 필드를 Color 마크로 드래그하면 색상 범례가 자동 생성됩니다.",
            ],
        }
    elif any(k in goal_lower for k in ["상관관계", "산점도", "scatter", "관계"]):
        chart_config = {
            "chart_type": "scatter",
            "chart_name": "산점도 (Scatter Plot)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. X축 측정값을 **Columns** 선반으로 드래그합니다.",
                "3. Y축 측정값을 **Rows** 선반으로 드래그합니다.",
                "4. 집계 단위가 되는 차원 필드를 **Detail** 마크로 드래그합니다.",
                "5. **Show Me** 패널에서 산점도를 선택합니다.",
            ],
            "advanced_steps": [
                "**추세선 추가:**",
                "Analytics 패널에서 Trend Line을 뷰로 드래그합니다. 선형, 다항식 등을 선택할 수 있습니다.",
                "**클러스터 분석:**",
                "Analytics 패널에서 Cluster를 드래그하여 자동 클러스터링을 적용합니다.",
                "**레이블로 점 식별:**",
                "범주 필드를 Label 마크로 드래그하면 각 점에 이름이 표시됩니다.",
                "**사분면 분석:**",
                "Reference Line을 X와 Y 축 모두에 추가하여 사분면을 구분합니다.",
            ],
        }
    elif any(k in goal_lower for k in ["분포", "히스토그램", "histogram", "빈도"]):
        chart_config = {
            "chart_type": "bar",
            "chart_name": "히스토그램 (Histogram)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. 수치형 측정값을 **Columns** 선반으로 드래그합니다.",
                "3. **Show Me** 패널에서 히스토그램을 선택합니다.",
                "4. 자동 생성된 구간(bin)을 우클릭 → Edit to 조정합니다.",
                "5. 빈도(CNT) 또는 비율(%)을 Rows에 배치합니다.",
            ],
            "advanced_steps": [
                "**Bin 크기 최적화:**",
                "차원 필드의 bin을 우클릭 → Edit → Size of bins 값을 조정합니다.",
                "**정규분포 곡선 오버레이:**",
                "계산 필드로 정규분포 함수를 정의하여 Reference Band로 추가합니다.",
                "**누적 분포 표시:**",
                "Quick Table Calculation → Running Total을 적용하면 누적 분포를 확인할 수 있습니다.",
            ],
        }
    elif any(k in goal_lower for k in ["지역", "맵", "map", "지도", "region"]):
        chart_config = {
            "chart_type": "map",
            "chart_name": "지도 (Map)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. 지역 필드(국가, 시/도 등)를 더블클릭하면 자동으로 지도가 생성됩니다.",
                "3. 측정값을 **Color** 마크로 드래그하면 단계구분도(Choropleth)가 됩니다.",
                "4. Map 메뉴 → Map Layers에서 배경 지도 스타일을 변경합니다.",
                "5. 필터를 추가하여 특정 지역을 집중 분석합니다.",
            ],
            "advanced_steps": [
                "**커스텀 지오코딩:**",
                "지역명이 Tableau에서 인식되지 않으면 Map → Geocoding → Import Custom Geocoding으로 커스텀 좌표를 등록합니다.",
                "**Filled Map vs Point Map:**",
                "Marks 카드에서 Filled Map(면 채우기) 또는 Circle(점 표시)을 선택합니다.",
                "**지역 계층 구조:**",
                "국가 → 시도 → 시군구 계층을 드릴다운할 수 있도록 계층(Hierarchy)을 생성합니다.",
                "**LOD로 지역별 집계:**",
                "```\n{ FIXED [Region] : SUM([Revenue]) }\n```",
            ],
        }
    else:
        chart_config = {
            "chart_type": "bar",
            "chart_name": "막대 차트 (기본 권장)",
            "basic_steps": [
                "1. Tableau Desktop을 열고 데이터 소스에 연결합니다.",
                "2. 차원 필드를 **Rows** 선반으로 드래그합니다.",
                "3. 측정값을 **Columns** 선반으로 드래그합니다.",
                "4. **Show Me** 패널에서 적합한 차트 유형을 선택합니다.",
                "5. 색상, 크기, 레이블 마크를 활용하여 추가 정보를 표현합니다.",
            ],
            "advanced_steps": [
                "**Show Me 패널 활용:**",
                "데이터 유형과 분석 목적에 따라 Show Me가 적합한 차트 유형을 자동 추천합니다.",
                "**계산 필드 생성:**",
                "Analysis → Create Calculated Field에서 비율, 증감률 등의 파생 지표를 만듭니다.",
                "**대시보드 구성:**",
                "여러 시트를 Dashboard 탭에서 조합하고 Action 필터로 인터랙티브하게 연결합니다.",
            ],
        }

    lines = [f"## Tableau 시각화 가이드: {chart_goal}", ""]
    lines.append(f"**권장 차트 유형**: {chart_config['chart_name']}")
    lines.append(f"**generate_twbx chart_type 값**: `\"{chart_config['chart_type']}\"`")

    if data_columns:
        lines.append(f"**활용 컬럼**: {', '.join(data_columns)}")
    lines.append("")

    if detail_level == "basic":
        lines.append("### 핵심 단계")
        for step in chart_config["basic_steps"]:
            lines.append(step)
    else:
        lines.append("### 기본 단계")
        for step in chart_config["basic_steps"]:
            lines.append(step)
        lines.append("")
        lines.append("### 고급 설정")
        for step in chart_config["advanced_steps"]:
            lines.append(step)

    lines.append("")
    lines.append("---")
    lines.append(f"이 시각화를 .twbx 파일로 생성하려면 `generate_twbx` 도구를 사용하세요.")

    return "\n".join(lines)
