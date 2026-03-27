"""비즈니스 분석 도구 — revenue, rfm, ltv, churn, pareto, growth."""
import logging
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select


def _fetch_df(conn_id: str, sql: str):
    """SQL 실행 → (DataFrame, "") 또는 (None, error_msg)."""
    err = _validate_select(sql)
    if err:
        return None, f"[ERROR] {err}"
    if conn_id not in _connections:
        return None, f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."
    try:
        conn = _get_conn(_connections[conn_id])
        try:
            df = pd.read_sql(sql, conn)
            return df, ""
        finally:
            conn.close()
    except Exception as e:
        return None, f"[ERROR] 쿼리 실행 실패: {e}"


def revenue_analysis(
    conn_id: str,
    sql: str,
    revenue_col: str,
    time_col: str,
    period: str = "month",
) -> str:
    """[Business] 기간별 매출 합계, 누적 매출, 전기 대비 증감률 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        revenue_col: 매출 수치 컬럼명
        time_col: 날짜/시간 컬럼명
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    period_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
    if period not in period_map:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(period_map.keys())}"

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [revenue_col, time_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
        agg = df[revenue_col].resample(period_map[period]).sum().reset_index()
        agg.columns = ["period", "revenue"]
        agg["cumulative"] = agg["revenue"].cumsum()
        agg["growth_pct"] = agg["revenue"].pct_change() * 100

        lines = [f"## 매출 분석 ({period} 단위)\n"]
        lines.append("| 기간 | 매출 | 누적 매출 | 전기 대비 증감률(%) |")
        lines.append("|------|------|-----------|---------------------|")
        for _, row in agg.iterrows():
            period_str = str(row["period"])[:10]
            rev = f"{row['revenue']:,.2f}"
            cum = f"{row['cumulative']:,.2f}"
            growth = "—" if pd.isna(row["growth_pct"]) else f"{row['growth_pct']:+.1f}%"
            lines.append(f"| {period_str} | {rev} | {cum} | {growth} |")

        total = agg["revenue"].sum()
        avg = agg["revenue"].mean()
        best_idx = agg["revenue"].idxmax()
        worst_idx = agg["revenue"].idxmin()
        best_period = str(agg.loc[best_idx, "period"])[:10]
        worst_period = str(agg.loc[worst_idx, "period"])[:10]

        lines.append(f"\n### 요약 통계")
        lines.append(f"- **총 매출**: {total:,.2f}")
        lines.append(f"- **기간 평균 매출**: {avg:,.2f}")
        lines.append(f"- **최고 기간**: {best_period} ({agg.loc[best_idx, 'revenue']:,.2f})")
        lines.append(f"- **최저 기간**: {worst_period} ({agg.loc[worst_idx, 'revenue']:,.2f})")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 매출 분석 실패: {e}"


def rfm_analysis(
    conn_id: str,
    sql: str,
    customer_col: str,
    date_col: str,
    revenue_col: str,
    snapshot_date: Optional[str] = None,
) -> str:
    """[Business] RFM(Recency, Frequency, Monetary) 고객 세그먼트 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        customer_col: 고객 식별 컬럼명
        date_col: 구매 날짜 컬럼명
        revenue_col: 구매 금액 컬럼명
        snapshot_date: 기준일 (None이면 데이터 최신일)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [customer_col, date_col, revenue_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[date_col] = pd.to_datetime(df[date_col])
        snap = pd.to_datetime(snapshot_date) if snapshot_date else df[date_col].max()

        rfm = df.groupby(customer_col).agg(
            recency=(date_col, lambda x: (snap - x.max()).days),
            frequency=(date_col, "count"),
            monetary=(revenue_col, "sum"),
        ).reset_index()

        # 5분위 점수화 (Recency는 낮을수록 좋으므로 역순)
        def safe_qcut(s, labels):
            try:
                return pd.qcut(s, q=5, labels=labels, duplicates="drop")
            except Exception:
                return pd.Series([3] * len(s), index=s.index)

        rfm["r_score"] = safe_qcut(rfm["recency"], labels=[5, 4, 3, 2, 1])
        rfm["f_score"] = safe_qcut(rfm["frequency"], labels=[1, 2, 3, 4, 5])
        rfm["m_score"] = safe_qcut(rfm["monetary"], labels=[1, 2, 3, 4, 5])
        rfm["rfm_score"] = rfm["r_score"].astype(int) + rfm["f_score"].astype(int) + rfm["m_score"].astype(int)

        def segment(row):
            r, f, m, total = int(row["r_score"]), int(row["f_score"]), int(row["m_score"]), int(row["rfm_score"])
            if total >= 13:
                return "Champion"
            elif r + f >= 9:
                return "Loyal"
            elif r <= 2 and f + m >= 6:
                return "At_Risk"
            elif total <= 5:
                return "Lost"
            else:
                return "Others"

        rfm["segment"] = rfm.apply(segment, axis=1)

        seg_summary = rfm.groupby("segment").agg(
            고객수=(customer_col, "count"),
            평균_Recency=("recency", "mean"),
            평균_Frequency=("frequency", "mean"),
            평균_Monetary=("monetary", "mean"),
        ).reset_index()

        lines = [f"## RFM 분석 (기준일: {str(snap)[:10]})\n"]
        lines.append("### 세그먼트별 고객 수\n")
        lines.append("| 세그먼트 | 고객 수 | 평균 Recency(일) | 평균 Frequency | 평균 Monetary |")
        lines.append("|----------|---------|-----------------|----------------|---------------|")
        for _, row in seg_summary.iterrows():
            lines.append(
                f"| {row['segment']} | {int(row['고객수']):,} | "
                f"{row['평균_Recency']:.1f} | {row['평균_Frequency']:.1f} | {row['평균_Monetary']:,.2f} |"
            )

        lines.append(f"\n### RFM 전체 요약 (상위 10개 고객)\n")
        lines.append(f"| {customer_col} | Recency | Frequency | Monetary | R | F | M | 세그먼트 |")
        lines.append("|------|---------|-----------|----------|---|---|---|----------|")
        for _, row in rfm.nlargest(10, "rfm_score").iterrows():
            lines.append(
                f"| {row[customer_col]} | {int(row['recency'])} | {int(row['frequency'])} | "
                f"{row['monetary']:,.2f} | {int(row['r_score'])} | {int(row['f_score'])} | "
                f"{int(row['m_score'])} | {row['segment']} |"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] RFM 분석 실패: {e}"


def ltv_analysis(
    conn_id: str,
    sql: str,
    customer_col: str,
    revenue_col: str,
    date_col: str,
    periods: int = 12,
) -> str:
    """[Business] 고객 생애 가치(LTV) 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        customer_col: 고객 식별 컬럼명
        revenue_col: 구매 금액 컬럼명
        date_col: 구매 날짜 컬럼명
        periods: 예측 기간(월 수)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [customer_col, revenue_col, date_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[date_col] = pd.to_datetime(df[date_col])
        date_range_months = max(
            (df[date_col].max() - df[date_col].min()).days / 30.0, 1.0
        )

        customer_stats = df.groupby(customer_col).agg(
            total_revenue=(revenue_col, "sum"),
            order_count=(date_col, "count"),
        ).reset_index()

        customer_stats["aov"] = customer_stats["total_revenue"] / customer_stats["order_count"]
        customer_stats["monthly_freq"] = customer_stats["order_count"] / date_range_months
        customer_stats["ltv"] = customer_stats["aov"] * customer_stats["monthly_freq"] * periods

        top20 = customer_stats.nlargest(20, "ltv")

        lines = [f"## LTV 분석 (예측 기간: {periods}개월)\n"]
        lines.append(f"| {customer_col} | 총 매출 | 주문 수 | AOV | 월 빈도 | 예상 LTV |")
        lines.append("|------|---------|---------|-----|---------|----------|")
        for _, row in top20.iterrows():
            lines.append(
                f"| {row[customer_col]} | {row['total_revenue']:,.2f} | "
                f"{int(row['order_count'])} | {row['aov']:,.2f} | "
                f"{row['monthly_freq']:.3f} | {row['ltv']:,.2f} |"
            )

        total_ltv = customer_stats["ltv"].sum()
        avg_ltv = customer_stats["ltv"].mean()
        median_ltv = customer_stats["ltv"].median()

        lines.append(f"\n### 전체 LTV 통계")
        lines.append(f"- **고객 수**: {len(customer_stats):,}")
        lines.append(f"- **총 예상 LTV**: {total_ltv:,.2f}")
        lines.append(f"- **평균 LTV**: {avg_ltv:,.2f}")
        lines.append(f"- **중앙값 LTV**: {median_ltv:,.2f}")
        lines.append(f"- **데이터 기간**: {date_range_months:.1f}개월")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] LTV 분석 실패: {e}"


def churn_analysis(
    conn_id: str,
    sql: str,
    customer_col: str,
    date_col: str,
    inactivity_days: int = 90,
) -> str:
    """[Business] 고객 이탈 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        customer_col: 고객 식별 컬럼명
        date_col: 구매/활동 날짜 컬럼명
        inactivity_days: 이탈 기준 비활동 일수 (기본 90일)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [customer_col, date_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[date_col] = pd.to_datetime(df[date_col])
        snapshot = df[date_col].max()

        last_purchase = df.groupby(customer_col)[date_col].max().reset_index()
        last_purchase.columns = [customer_col, "last_date"]
        last_purchase["days_since"] = (snapshot - last_purchase["last_date"]).dt.days

        active_threshold = inactivity_days / 3
        at_risk_threshold = inactivity_days

        def classify(days):
            if days < active_threshold:
                return "활성"
            elif days < at_risk_threshold:
                return "이탈 위험"
            else:
                return "이탈"

        last_purchase["segment"] = last_purchase["days_since"].apply(classify)

        total = len(last_purchase)
        seg_counts = last_purchase["segment"].value_counts()

        lines = [f"## 이탈 분석 (기준일: {str(snapshot)[:10]}, 비활동 기준: {inactivity_days}일)\n"]
        lines.append("### 세그먼트별 고객 현황\n")
        lines.append("| 세그먼트 | 고객 수 | 비율(%) | 기준 |")
        lines.append("|----------|---------|---------|------|")
        seg_info = {
            "활성": f"최근 {active_threshold:.0f}일 이내",
            "이탈 위험": f"{active_threshold:.0f}~{at_risk_threshold}일",
            "이탈": f"{at_risk_threshold}일 초과",
        }
        for seg in ["활성", "이탈 위험", "이탈"]:
            cnt = seg_counts.get(seg, 0)
            pct = cnt / total * 100 if total > 0 else 0
            lines.append(f"| {seg} | {cnt:,} | {pct:.1f}% | {seg_info[seg]} |")

        at_risk = last_purchase[last_purchase["segment"] == "이탈 위험"].nlargest(10, "days_since")
        if not at_risk.empty:
            lines.append(f"\n### 이탈 위험 고객 상위 10개\n")
            lines.append(f"| {customer_col} | 마지막 구매일 | 경과일 |")
            lines.append("|------|-------------|--------|")
            for _, row in at_risk.iterrows():
                lines.append(
                    f"| {row[customer_col]} | {str(row['last_date'])[:10]} | {int(row['days_since'])}일 |"
                )

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 이탈 분석 실패: {e}"


def pareto_analysis(
    conn_id: str,
    sql: str,
    category_col: str,
    value_col: str,
) -> str:
    """[Business] 파레토(80/20) 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        category_col: 카테고리 컬럼명
        value_col: 값 수치 컬럼명
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [category_col, value_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        agg = df.groupby(category_col)[value_col].sum().reset_index()
        agg = agg.sort_values(value_col, ascending=False).reset_index(drop=True)
        total = agg[value_col].sum()
        if total == 0:
            return "[ERROR] value_col 합계가 0입니다."

        agg["contribution_pct"] = agg[value_col] / total * 100
        agg["cumulative_pct"] = agg["contribution_pct"].cumsum()
        agg["group"] = agg["cumulative_pct"].apply(lambda x: "상위 (80% 이내)" if x <= 80 else "하위 (80% 초과)")

        pareto_count = (agg["cumulative_pct"] <= 80).sum()
        pareto_pct = pareto_count / len(agg) * 100

        lines = ["## 파레토 분석 (80/20 규칙)\n"]
        lines.append(f"| {category_col} | {value_col} | 기여도(%) | 누적 기여도(%) | 그룹 |")
        lines.append("|------|------|-----------|----------------|------|")
        for _, row in agg.iterrows():
            lines.append(
                f"| {row[category_col]} | {row[value_col]:,.2f} | "
                f"{row['contribution_pct']:.1f}% | {row['cumulative_pct']:.1f}% | {row['group']} |"
            )

        lines.append(f"\n### 요약")
        lines.append(
            f"- **상위 {pareto_count}개({pareto_pct:.1f}%)가 전체의 80% 기여**"
        )
        lines.append(f"- 전체 항목 수: {len(agg)}")
        lines.append(f"- 전체 합계: {total:,.2f}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 파레토 분석 실패: {e}"


def growth_analysis(
    conn_id: str,
    sql: str,
    metric_col: str,
    time_col: str,
    period: str = "month",
) -> str:
    """[Business] 성장률 분석 (MoM, QoQ, YoY, CAGR).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        metric_col: 성장률을 측정할 수치 컬럼명
        time_col: 날짜/시간 컬럼명
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    period_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
    if period not in period_map:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(period_map.keys())}"

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [metric_col, time_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
        agg = df[metric_col].resample(period_map[period]).sum()

        # lag 설정
        lag_map = {"day": (1, 7, 365), "week": (1, 4, 52), "month": (1, 3, 12), "quarter": (1, 2, 4), "year": (1, 1, 1)}
        lag_mom, lag_qoq, lag_yoy = lag_map[period]

        result = pd.DataFrame({"value": agg})
        result["MoM(%)"] = result["value"].pct_change(lag_mom) * 100
        if lag_qoq != lag_mom:
            result["QoQ(%)"] = result["value"].pct_change(lag_qoq) * 100
        if lag_yoy != lag_mom and lag_yoy != lag_qoq:
            result["YoY(%)"] = result["value"].pct_change(lag_yoy) * 100

        growth_cols = [c for c in ["MoM(%)", "QoQ(%)", "YoY(%)"] if c in result.columns]

        lines = [f"## 성장률 분석 ({period} 단위)\n"]
        header = "| 기간 | 값 | " + " | ".join(growth_cols) + " |"
        sep = "|------|------|" + "------|" * len(growth_cols)
        lines.append(header)
        lines.append(sep)

        for idx, row in result.iterrows():
            period_str = str(idx)[:10]
            val = f"{row['value']:,.2f}"
            growth_vals = []
            for gc in growth_cols:
                if pd.isna(row[gc]):
                    growth_vals.append("—")
                else:
                    growth_vals.append(f"{row[gc]:+.1f}%")
            lines.append(f"| {period_str} | {val} | " + " | ".join(growth_vals) + " |")

        # CAGR 계산
        n = len(agg)
        if n >= 2:
            first_val = agg.iloc[0]
            last_val = agg.iloc[-1]
            years_map = {"day": 365, "week": 52, "month": 12, "quarter": 4, "year": 1}
            years = (n - 1) / years_map[period]
            if first_val > 0 and years > 0:
                cagr = ((last_val / first_val) ** (1 / years) - 1) * 100
                lines.append(f"\n### CAGR (연평균 성장률)")
                lines.append(f"- **CAGR**: {cagr:+.2f}% (기간: {years:.2f}년)")
            else:
                lines.append(f"\n### CAGR: 계산 불가 (첫 값이 0이거나 기간 부족)")
        else:
            lines.append(f"\n### CAGR: 데이터 부족 (2개 이상의 기간 필요)")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 성장률 분석 실패: {e}"
