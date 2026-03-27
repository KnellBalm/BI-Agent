"""BI 도구 선택기 — 분석 목표 기반 MCP 도구 추천 헬퍼."""
from __future__ import annotations

_TOOL_CATALOG = {
    "매출": {
        "keywords": ["매출", "revenue", "sales", "수익", "gmv"],
        "primary": [
            ("revenue_analysis", "기간별 매출 집계 및 성장률 분석", "conn_id, sql, time_col, revenue_col"),
            ("trend_analysis", "시계열 추세 분석", "conn_id, sql, time_col, metric_col"),
            ("growth_analysis", "성장률 계산", "conn_id, sql, time_col, value_col"),
        ],
        "secondary": [
            ("cohort_analysis", "코호트별 매출 분석"),
            ("pareto_analysis", "80/20 매출 기여 분석"),
            ("linear_trend_forecast", "선형 추세 예측"),
        ],
        "workflow": [
            "1. revenue_analysis로 전체 매출 현황 파악",
            "2. trend_analysis로 추세 확인",
            "3. growth_analysis로 성장률 계산",
            "4. linear_trend_forecast로 미래 예측",
        ],
        "example": {
            "tool": "revenue_analysis",
            "params": 'conn_id="mydb",\n    sql="SELECT date, revenue FROM sales",\n    time_col="date",\n    revenue_col="revenue"',
        },
    },
    "이탈": {
        "keywords": ["이탈", "churn", "churning", "retention", "유지"],
        "primary": [
            ("churn_analysis", "이탈률 분석", "conn_id, sql, user_col, date_col, status_col"),
            ("retention_curve", "코호트별 유지율 곡선", "conn_id, sql, user_col, signup_col, activity_col"),
        ],
        "secondary": [
            ("ttest_independent", "이탈/유지 그룹 특성 비교"),
            ("feature_adoption", "기능 사용률과 이탈 관계"),
            ("segment_analysis", "이탈 세그먼트 분석"),
        ],
        "workflow": [
            "1. churn_analysis로 이탈률 측정",
            "2. retention_curve로 유지 패턴 확인",
            "3. ttest_independent로 이탈/유지 그룹 비교",
            "4. segment_analysis로 고위험 세그먼트 파악",
        ],
        "example": {
            "tool": "churn_analysis",
            "params": 'conn_id="mydb",\n    sql="SELECT user_id, signup_date, status FROM users",\n    user_col="user_id",\n    date_col="signup_date",\n    status_col="status"',
        },
    },
    "ab_test": {
        "keywords": ["a/b", "ab", "ab test", "실험", "테스트"],
        "primary": [
            ("ab_test_analysis", "A/B 테스트 전환율 비교", "conn_id, sql, group_col, conversion_col"),
            ("ttest_independent", "독립 표본 t-검정", "conn_id, sql, group_col, value_col"),
        ],
        "secondary": [
            ("chi_square_test", "범주형 결과 카이제곱 검정"),
            ("confidence_interval", "전환율 신뢰구간"),
            ("sampling_error", "표본 오차 계산"),
        ],
        "workflow": [
            "1. ab_test_analysis로 전환율 비교",
            "2. ttest_independent로 평균 차이 검정",
            "3. chi_square_test로 범주형 결과 검정",
            "4. confidence_interval로 신뢰구간 확인",
        ],
        "example": {
            "tool": "ab_test_analysis",
            "params": 'conn_id="mydb",\n    sql="SELECT group, converted FROM experiments",\n    group_col="group",\n    conversion_col="converted"',
        },
    },
    "예측": {
        "keywords": ["예측", "forecast", "prediction", "미래", "추세"],
        "primary": [
            ("linear_trend_forecast", "선형 추세 예측", "conn_id, sql, time_col, metric_col, forecast_periods"),
            ("moving_average_forecast", "이동평균 예측", "conn_id, sql, time_col, metric_col, window"),
            ("exponential_smoothing_forecast", "지수평활 예측", "conn_id, sql, time_col, metric_col, alpha"),
        ],
        "secondary": [
            ("trend_analysis", "과거 추세 분석"),
            ("normality_test", "데이터 분포 확인"),
        ],
        "workflow": [
            "1. trend_analysis로 과거 추세 파악",
            "2. linear_trend_forecast로 선형 예측",
            "3. moving_average_forecast로 단기 예측",
            "4. 결과 비교 후 최적 모델 선택",
        ],
        "example": {
            "tool": "linear_trend_forecast",
            "params": 'conn_id="mydb",\n    sql="SELECT date, metric FROM daily_stats",\n    time_col="date",\n    metric_col="metric",\n    forecast_periods=30',
        },
    },
    "이상치": {
        "keywords": ["이상치", "anomaly", "outlier", "비정상", "오류"],
        "primary": [
            ("iqr_anomaly_detection", "IQR 기반 이상치 탐지", "conn_id, sql, column"),
            ("zscore_anomaly_detection", "Z-Score 기반 이상치 탐지", "conn_id, sql, column, threshold"),
        ],
        "secondary": [
            ("boxplot_summary", "박스플롯 요약 통계"),
            ("descriptive_stats", "기술 통계로 분포 확인"),
        ],
        "workflow": [
            "1. descriptive_stats로 분포 확인",
            "2. iqr_anomaly_detection으로 이상치 탐지",
            "3. zscore_anomaly_detection으로 교차 검증",
            "4. 이상치 행 제거 후 재분석",
        ],
        "example": {
            "tool": "iqr_anomaly_detection",
            "params": 'conn_id="mydb",\n    sql="SELECT amount FROM transactions",\n    column="amount"',
        },
    },
    "통계": {
        "keywords": ["통계", "분포", "distribution", "정규성", "평균", "분산", "상관"],
        "primary": [
            ("descriptive_stats", "기술 통계 (평균/표준편차/분위수)", "conn_id, sql, columns"),
            ("correlation_analysis", "상관계수 행렬", "conn_id, sql"),
            ("distribution_analysis", "분포 분석", "conn_id, sql, column"),
        ],
        "secondary": [
            ("normality_test", "정규성 검정"),
            ("boxplot_summary", "박스플롯 요약"),
            ("percentile_analysis", "백분위수 분석"),
        ],
        "workflow": [
            "1. descriptive_stats로 기본 통계 확인",
            "2. normality_test로 정규성 검정",
            "3. distribution_analysis로 분포 시각화",
            "4. correlation_analysis로 변수 간 관계 파악",
        ],
        "example": {
            "tool": "descriptive_stats",
            "params": 'conn_id="mydb",\n    sql="SELECT price, quantity FROM products",\n    columns=["price", "quantity"]',
        },
    },
    "세분화": {
        "keywords": ["세분화", "segment", "rfm", "ltv", "고객군"],
        "primary": [
            ("rfm_analysis", "RFM 고객 세분화", "conn_id, sql, user_col, date_col, revenue_col"),
            ("segment_analysis", "커스텀 세그먼트 분석", "conn_id, sql, segment_col, metric_col"),
            ("ltv_analysis", "고객 생애 가치 분석", "conn_id, sql, user_col, revenue_col"),
        ],
        "secondary": [
            ("cohort_analysis", "코호트 분석"),
            ("churn_analysis", "세그먼트별 이탈률"),
        ],
        "workflow": [
            "1. rfm_analysis로 RFM 세그먼트 정의",
            "2. ltv_analysis로 세그먼트별 LTV 계산",
            "3. segment_analysis로 세그먼트별 지표 비교",
            "4. churn_analysis로 세그먼트별 이탈률",
        ],
        "example": {
            "tool": "rfm_analysis",
            "params": 'conn_id="mydb",\n    sql="SELECT user_id, order_date, amount FROM orders",\n    user_col="user_id",\n    date_col="order_date",\n    revenue_col="amount"',
        },
    },
    "퍼널": {
        "keywords": ["퍼널", "funnel", "전환", "conversion", "드롭오프", "dropoff"],
        "primary": [
            ("funnel_analysis", "퍼널 단계별 전환율", "conn_id, sql, stage_col, count_col"),
            ("conversion_funnel", "마케팅 전환 퍼널", "conn_id, sql, stage_col, users_col"),
            ("user_journey", "사용자 여정 분석", "conn_id, sql, user_col, event_col, time_col"),
        ],
        "secondary": [
            ("ab_test_analysis", "퍼널 A/B 테스트"),
            ("cohort_analysis", "코호트별 퍼널"),
        ],
        "workflow": [
            "1. funnel_analysis로 전체 퍼널 전환율 확인",
            "2. 드롭오프가 가장 큰 단계 파악",
            "3. user_journey로 사용자 경로 분석",
            "4. ab_test_analysis로 개선안 검증",
        ],
        "example": {
            "tool": "funnel_analysis",
            "params": 'conn_id="mydb",\n    sql="SELECT stage, user_count FROM funnel_data",\n    stage_col="stage",\n    count_col="user_count"',
        },
    },
    "마케팅": {
        "keywords": ["마케팅", "marketing", "캠페인", "campaign", "채널", "channel", "roas", "cac"],
        "primary": [
            ("campaign_performance", "캠페인 성과 분석", "conn_id, sql, campaign_col, metric_col"),
            ("channel_attribution", "채널 기여도 분석", "conn_id, sql, channel_col, conversion_col"),
            ("cac_roas", "CAC/ROAS 계산", "conn_id, sql, cost_col, revenue_col, users_col"),
        ],
        "secondary": [
            ("conversion_funnel", "마케팅 전환 퍼널"),
            ("cohort_analysis", "획득 코호트 분석"),
        ],
        "workflow": [
            "1. campaign_performance로 캠페인별 성과 확인",
            "2. channel_attribution으로 채널 기여도 분석",
            "3. cac_roas로 ROI 계산",
            "4. conversion_funnel로 채널별 전환 퍼널",
        ],
        "example": {
            "tool": "campaign_performance",
            "params": 'conn_id="mydb",\n    sql="SELECT campaign, clicks, conversions FROM ads",\n    campaign_col="campaign",\n    metric_col="conversions"',
        },
    },
    "시각화": {
        "keywords": ["시각화", "chart", "dashboard", "tableau", "그래프", "visualize"],
        "primary": [
            ("generate_dashboard", "Chart.js HTML 대시보드 생성", "data, charts, title"),
            ("generate_twbx", "Tableau TWBX 패키지 생성", "data, chart_type, title"),
        ],
        "secondary": [
            ("chart_from_file", "파일 데이터로 차트 생성"),
            ("visualize_advisor", "시각화 방법 추천 (헬퍼)"),
            ("dashboard_design_guide", "대시보드 레이아웃 설계 (헬퍼)"),
        ],
        "workflow": [
            "1. visualize_advisor로 적합한 차트 타입 확인",
            "2. 데이터를 마크다운 테이블로 준비",
            "3. generate_dashboard 또는 generate_twbx 호출",
            "4. 결과 파일 확인",
        ],
        "example": {
            "tool": "generate_dashboard",
            "params": 'data="| 날짜 | 매출 |\\n| 2024-01 | 1000 |",\n    charts=[{"type": "line", "x": "날짜", "y": "매출"}],\n    title="매출 대시보드"',
        },
    },
}

_DOMAIN_ADVICE = {
    "ecommerce": "이커머스 도메인: orders, products, customers 테이블 중심으로 분석하세요. GMV·AOV·구매 빈도가 핵심 지표입니다.",
    "saas": "SaaS 도메인: 구독·활성화·이탈·NRR 지표를 우선 확인하세요. 코호트별 리텐션이 가장 중요한 지표입니다.",
    "marketing": "마케팅 도메인: 채널별 CAC·ROAS·전환율을 비교하세요. UTM 파라미터로 유입 채널을 구분하는 것이 일반적입니다.",
}

_CONSTRAINT_ADVICE = {
    "scipy 없음": "scipy가 없으면 `ttest_independent`, `chi_square_test`, `normality_test` 도구는 사용할 수 없습니다. 대신 `descriptive_stats`와 `confidence_interval`을 활용하세요.",
    "소규모 데이터": "소규모 데이터(<100행)의 경우 통계 검정 결과의 신뢰도가 낮을 수 있습니다. `descriptive_stats`와 `boxplot_summary`로 탐색적 분석을 우선하세요.",
}


def _match_categories(analysis_goal: str) -> list[str]:
    goal_lower = analysis_goal.lower()
    matched = []
    for category, info in _TOOL_CATALOG.items():
        for kw in info["keywords"]:
            if kw in goal_lower:
                matched.append(category)
                break
    return matched


def bi_tool_selector(
    analysis_goal: str,
    data_domain: str = "",
    constraints: str = "",
) -> str:
    """[Helper] 분석 목표에 맞는 BI 도구를 추천하고 워크플로우를 안내합니다.

    91개 MCP 도구 중 analysis_goal 키워드를 분석하여 핵심/보조 도구를 추천하고,
    파라미터 예시와 단계별 워크플로우를 제공합니다.

    Args:
        analysis_goal: 분석 목표 설명. 예: "매출 추이 분석", "A/B 테스트 결과 검증",
                       "고객 이탈 원인 파악", "퍼널 분석"
        data_domain: 데이터 도메인. 예: "ecommerce", "saas", "marketing" (선택)
        constraints: 제약 조건. 예: "scipy 없음", "소규모 데이터 (<100행)" (선택)
    """
    matched = _match_categories(analysis_goal)

    lines: list[str] = [f"## BI 도구 추천: {analysis_goal}", ""]

    if not matched:
        lines += [
            "분석 목표에서 특정 카테고리를 인식하지 못했습니다.",
            "",
            "지원하는 분석 카테고리:",
            "- **매출** (revenue, sales, GMV)",
            "- **이탈** (churn, retention)",
            "- **A/B 테스트** (실험, 전환)",
            "- **예측** (forecast, 미래 추세)",
            "- **이상치** (anomaly, outlier)",
            "- **통계** (분포, 상관, 정규성)",
            "- **세분화** (RFM, LTV, 고객군)",
            "- **퍼널** (funnel, 전환율, 드롭오프)",
            "- **마케팅** (캠페인, 채널, ROAS)",
            "- **시각화** (chart, dashboard, tableau)",
            "",
            "분석 목표를 더 구체적으로 입력해 주세요. 예: `bi_tool_selector('매출 추이 분석')`",
        ]
        return "\n".join(lines)

    for category in matched:
        info = _TOOL_CATALOG[category]

        # 핵심 도구 테이블
        lines += [
            "### 핵심 도구",
            "",
            "| 도구 | 설명 | 주요 파라미터 |",
            "|------|------|--------------|",
        ]
        for tool_name, desc, params in info["primary"]:
            lines.append(f"| `{tool_name}` | {desc} | {params} |")

        # 보조 도구
        lines += ["", "### 보조 도구"]
        for tool_name, desc in info["secondary"]:
            lines.append(f"- `{tool_name}` — {desc}")

        # 워크플로우
        lines += ["", "### 권장 분석 순서"]
        for step in info["workflow"]:
            lines.append(step)

        # 파라미터 예시
        ex = info["example"]
        lines += [
            "",
            "### 파라미터 예시",
            "",
            "```python",
            f"# 1단계: {info['workflow'][0].split('. ', 1)[-1]}",
            f"result = {ex['tool']}(",
            f"    {ex['params']}",
            ")",
            "```",
        ]

        lines.append("")

    # 도메인 특화 조언
    if data_domain:
        domain_lower = data_domain.lower()
        advice = None
        for key, text in _DOMAIN_ADVICE.items():
            if key in domain_lower:
                advice = text
                break
        if advice is None:
            advice = f"{data_domain} 도메인에 맞는 핵심 지표와 테이블 구조를 먼저 파악하세요."
        lines += [f"### 도메인 조언 ({data_domain})", "", advice, ""]

    # 제약 조건 반영
    if constraints:
        constraints_lower = constraints.lower()
        constraint_notes = []
        for key, text in _CONSTRAINT_ADVICE.items():
            if key in constraints_lower:
                constraint_notes.append(text)
        if not constraint_notes:
            constraint_notes.append(f"제약 조건 `{constraints}`을 고려하여 도구 선택 전 환경을 확인하세요.")
        lines += ["### 제약 조건 반영", ""]
        for note in constraint_notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines).rstrip()
