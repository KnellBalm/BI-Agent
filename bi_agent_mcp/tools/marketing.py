"""마케팅 분석 도구 — campaign_performance, channel_attribution, cac_roas, conversion_funnel."""
import logging
import pandas as pd
from typing import Optional

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


def campaign_performance(
    conn_id: str,
    sql: str,
    campaign_col: str,
    metric_cols: list,
    date_col: Optional[str] = None,
) -> str:
    """[Marketing] 캠페인별 성과 비교 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        campaign_col: 캠페인 구분 컬럼명
        metric_cols: 집계할 수치형 컬럼 목록 (예: ["impressions", "clicks", "conversions", "revenue"])
        date_col: 날짜 컬럼명 (기간별 트렌드 포함 시)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    if campaign_col not in df.columns:
        return f"[ERROR] campaign_col '{campaign_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    valid_metrics = [c for c in metric_cols if c in df.columns]
    if not valid_metrics:
        return f"[ERROR] metric_cols 중 유효한 컬럼이 없습니다: {metric_cols}"

    try:
        agg = df.groupby(campaign_col)[valid_metrics].sum().reset_index()

        # CTR, CVR 계산
        derived = []
        if "clicks" in agg.columns and "impressions" in agg.columns:
            agg["CTR(%)"] = (agg["clicks"] / agg["impressions"].replace(0, float("nan")) * 100).round(2)
            derived.append("CTR(%)")
        if "conversions" in agg.columns and "clicks" in agg.columns:
            agg["CVR(%)"] = (agg["conversions"] / agg["clicks"].replace(0, float("nan")) * 100).round(2)
            derived.append("CVR(%)")

        display_cols = [campaign_col] + valid_metrics + derived
        lines = ["## 캠페인 성과 분석\n"]
        lines.append("| " + " | ".join(display_cols) + " |")
        lines.append("|" + "------|" * len(display_cols))

        for _, row in agg.iterrows():
            vals = []
            for c in display_cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}" if not pd.isna(v) else "N/A")
                else:
                    vals.append(str(v))
            lines.append("| " + " | ".join(vals) + " |")

        # 최고 성과 캠페인 (primary metric = 첫 번째 metric_col)
        primary = valid_metrics[0]
        best_row = agg.loc[agg[primary].idxmax()]
        lines.append(f"\n### 최고 성과 캠페인 ({primary} 기준)")
        lines.append(f"- **{best_row[campaign_col]}**: {best_row[primary]:,.2f}")

        # 기간별 트렌드
        if date_col:
            if date_col not in df.columns:
                lines.append(f"\n[WARN] date_col '{date_col}'이 데이터에 없어 트렌드를 건너뜁니다.")
            else:
                try:
                    df[date_col] = pd.to_datetime(df[date_col])
                    trend = df.groupby([date_col, campaign_col])[valid_metrics].sum().reset_index()
                    trend = trend.sort_values(date_col)
                    lines.append("\n### 기간별 트렌드\n")
                    trend_cols = [date_col, campaign_col] + valid_metrics
                    lines.append("| " + " | ".join(trend_cols) + " |")
                    lines.append("|" + "------|" * len(trend_cols))
                    for _, row in trend.iterrows():
                        vals = []
                        for c in trend_cols:
                            v = row[c]
                            if isinstance(v, (float, int)) and not isinstance(v, bool):
                                vals.append(f"{v:,.2f}")
                            elif hasattr(v, "strftime"):
                                vals.append(str(v)[:10])
                            else:
                                vals.append(str(v))
                        lines.append("| " + " | ".join(vals) + " |")
                except Exception as e:
                    lines.append(f"\n[WARN] 트렌드 분석 실패: {e}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 캠페인 성과 분석 실패: {e}"


def channel_attribution(
    conn_id: str,
    sql: str,
    channel_col: str,
    conversion_col: str,
    revenue_col: Optional[str] = None,
    model: str = "last_touch",
) -> str:
    """[Marketing] 채널 어트리뷰션 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        channel_col: 채널 구분 컬럼명
        conversion_col: 전환 여부(0/1) 또는 전환 수 컬럼명
        revenue_col: 매출 컬럼명 (선택)
        model: "last_touch"|"first_touch"|"linear"
    """
    supported_models = ["last_touch", "first_touch", "linear"]
    if model not in supported_models:
        return f"[ERROR] model '{model}'은 지원하지 않습니다. 사용 가능: {supported_models}"

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [channel_col, conversion_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    if revenue_col and revenue_col not in df.columns:
        return f"[ERROR] revenue_col '{revenue_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        if model == "last_touch":
            # 마지막 채널에 100% 기여
            agg = df.groupby(channel_col)[conversion_col].sum().reset_index()
            agg.columns = [channel_col, "기여_전환수"]
            model_desc = "Last Touch: 마지막 채널에 전환의 100%를 기여합니다."
        elif model == "first_touch":
            # 첫 번째 채널에 100% 기여 (데이터 순서 기준)
            agg = df.groupby(channel_col)[conversion_col].sum().reset_index()
            agg.columns = [channel_col, "기여_전환수"]
            model_desc = "First Touch: 첫 번째 채널에 전환의 100%를 기여합니다."
        else:  # linear
            # 균등 분배: 각 행의 전환을 채널 수로 나눔
            total_channels = df[channel_col].nunique()
            df_copy = df.copy()
            df_copy["기여_전환수"] = df_copy[conversion_col] / total_channels
            agg = df_copy.groupby(channel_col)["기여_전환수"].sum().reset_index()
            model_desc = f"Linear: 전환을 모든 채널({total_channels}개)에 균등 분배합니다."

        total_conv = agg["기여_전환수"].sum()
        agg["기여율(%)"] = (agg["기여_전환수"] / total_conv * 100).round(2) if total_conv else 0
        agg = agg.sort_values("기여_전환수", ascending=False)

        display_cols = [channel_col, "기여_전환수", "기여율(%)"]

        if revenue_col:
            rev_agg = df.groupby(channel_col)[revenue_col].sum().reset_index()
            rev_agg.columns = [channel_col, "기여_매출"]
            if model == "linear":
                rev_agg["기여_매출"] = rev_agg["기여_매출"] / total_channels
            agg = agg.merge(rev_agg, on=channel_col, how="left")
            display_cols.append("기여_매출")

        lines = [f"## 채널 어트리뷰션 분석 ({model})\n"]
        lines.append(f"> {model_desc}\n")
        lines.append("| " + " | ".join(display_cols) + " |")
        lines.append("|" + "------|" * len(display_cols))

        for _, row in agg.iterrows():
            vals = []
            for c in display_cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}" if not pd.isna(v) else "N/A")
                else:
                    vals.append(str(v))
            lines.append("| " + " | ".join(vals) + " |")

        top_channel = agg.iloc[0][channel_col]
        top_conv = agg.iloc[0]["기여_전환수"]
        lines.append(f"\n### 최고 기여 채널")
        lines.append(f"- **{top_channel}**: 기여 전환 {top_conv:,.2f}건 ({agg.iloc[0]['기여율(%)']:.1f}%)")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 채널 어트리뷰션 분석 실패: {e}"


def cac_roas(
    conn_id: str,
    sql: str,
    channel_col: str,
    cost_col: str,
    revenue_col: str,
    conversions_col: Optional[str] = None,
) -> str:
    """[Marketing] 채널별 CAC / ROAS / ROI 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        channel_col: 채널 구분 컬럼명
        cost_col: 비용 컬럼명
        revenue_col: 매출 컬럼명
        conversions_col: 전환 수 컬럼명 (None이면 revenue > 0인 행 수로 대체)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [channel_col, cost_col, revenue_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    if conversions_col and conversions_col not in df.columns:
        return f"[ERROR] conversions_col '{conversions_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        groups = df.groupby(channel_col)
        agg_cost = groups[cost_col].sum()
        agg_revenue = groups[revenue_col].sum()

        if conversions_col:
            agg_conv = groups[conversions_col].sum()
        else:
            agg_conv = groups[revenue_col].apply(lambda x: (x > 0).sum())

        result = pd.DataFrame({
            "총비용": agg_cost,
            "총매출": agg_revenue,
            "전환수": agg_conv,
        }).reset_index()

        result["CAC"] = (result["총비용"] / result["전환수"].replace(0, float("nan"))).round(2)
        result["ROAS(%)"] = (result["총매출"] / result["총비용"].replace(0, float("nan")) * 100).round(2)
        result["ROI(%)"] = ((result["총매출"] - result["총비용"]) / result["총비용"].replace(0, float("nan")) * 100).round(2)

        result = result.sort_values("ROAS(%)", ascending=False)

        display_cols = [channel_col, "총비용", "총매출", "전환수", "CAC", "ROAS(%)", "ROI(%)"]
        lines = ["## 채널별 CAC / ROAS / ROI 분석\n"]
        lines.append("| " + " | ".join(display_cols) + " |")
        lines.append("|" + "------|" * len(display_cols))

        for _, row in result.iterrows():
            vals = []
            for c in display_cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}" if not pd.isna(v) else "N/A")
                else:
                    vals.append(str(v))
            lines.append("| " + " | ".join(vals) + " |")

        # 최효율 채널 (ROAS 기준)
        best = result.iloc[0]
        lines.append(f"\n### 최효율 채널 (ROAS 기준)")
        lines.append(f"- **{best[channel_col]}**: ROAS {best['ROAS(%)']:,.2f}%, ROI {best['ROI(%)']:,.2f}%, CAC {best['CAC']:,.2f}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] CAC/ROAS 분석 실패: {e}"


def conversion_funnel(
    conn_id: str,
    sql: str,
    stage_col: str,
    user_col: str,
    date_col: Optional[str] = None,
) -> str:
    """[Marketing] 퍼널 단계별 전환율 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        stage_col: 퍼널 단계 컬럼명 (예: "visit", "signup", "purchase")
        user_col: 사용자 식별 컬럼명
        date_col: 날짜 컬럼명 (기간별 트렌드 포함 시)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [stage_col, user_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        stages = df[stage_col].unique().tolist()
        stage_counts = df.groupby(stage_col)[user_col].nunique()

        # 단계 순서 유지 (데이터에 등장하는 순서)
        ordered_stages = df[stage_col].drop_duplicates().tolist()
        stage_counts = stage_counts.reindex(ordered_stages)

        first_val = stage_counts.iloc[0] if len(stage_counts) > 0 else 0

        lines = ["## 퍼널 전환율 분석\n"]
        lines.append("| 단계 | 고유 사용자 수 | 전 단계 대비 전환율(%) | 전체 대비 전환율(%) |")
        lines.append("|------|--------------|----------------------|-------------------|")

        bottleneck_stage = None
        bottleneck_rate = float("inf")

        for i, stage in enumerate(ordered_stages):
            count = stage_counts[stage]
            if i == 0:
                prev_conv = "—"
                total_conv = "100.0%"
            else:
                prev_count = stage_counts.iloc[i - 1]
                if prev_count > 0:
                    rate = count / prev_count * 100
                    prev_conv = f"{rate:.1f}%"
                    if rate < bottleneck_rate:
                        bottleneck_rate = rate
                        bottleneck_stage = stage
                else:
                    prev_conv = "N/A"
                total_conv = f"{count / first_val * 100:.1f}%" if first_val > 0 else "N/A"

            lines.append(f"| {stage} | {count:,} | {prev_conv} | {total_conv} |")

        if bottleneck_stage:
            lines.append(f"\n### 병목 지점 (가장 높은 이탈 단계)")
            lines.append(f"- **{bottleneck_stage}**: 전 단계 대비 전환율 {bottleneck_rate:.1f}%")

        # 기간별 트렌드
        if date_col:
            if date_col not in df.columns:
                lines.append(f"\n[WARN] date_col '{date_col}'이 데이터에 없어 트렌드를 건너뜁니다.")
            else:
                try:
                    df[date_col] = pd.to_datetime(df[date_col])
                    trend = df.groupby([date_col, stage_col])[user_col].nunique().reset_index()
                    trend = trend.sort_values([date_col, stage_col])
                    trend.columns = [date_col, stage_col, "고유_사용자수"]
                    lines.append("\n### 기간별 퍼널 트렌드\n")
                    trend_cols = [date_col, stage_col, "고유_사용자수"]
                    lines.append("| " + " | ".join(trend_cols) + " |")
                    lines.append("|" + "------|" * len(trend_cols))
                    for _, row in trend.iterrows():
                        date_str = str(row[date_col])[:10]
                        lines.append(f"| {date_str} | {row[stage_col]} | {row['고유_사용자수']:,} |")
                except Exception as e:
                    lines.append(f"\n[WARN] 기간별 트렌드 분석 실패: {e}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 퍼널 전환율 분석 실패: {e}"
