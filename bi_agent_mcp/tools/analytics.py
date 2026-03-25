"""BI 심층 분석 도구 — trend, correlation, distribution, segment, funnel, cohort, pivot, top_n."""
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
        df = pd.read_sql(sql, conn)
        conn.close()
        return df, ""
    except Exception as e:
        return None, f"[ERROR] 쿼리 실행 실패: {e}"


def trend_analysis(conn_id: str, sql: str, time_col: str, metric_cols: list, period: str = "month") -> str:
    """
    시계열 트렌드 분석. time_col 기준으로 period 단위 집계 후 전기 대비 증감률 계산.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        time_col: 날짜/시간 컬럼명
        metric_cols: 집계할 수치형 컬럼 목록
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if time_col not in df.columns:
        return f"[ERROR] time_col '{time_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    period_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
    if period not in period_map:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(period_map.keys())}"

    valid_cols = [c for c in metric_cols if c in df.columns]
    if not valid_cols:
        return f"[ERROR] metric_cols 중 유효한 컬럼이 없습니다: {metric_cols}"

    try:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
        agg = df[valid_cols].resample(period_map[period]).sum()

        lines = [f"## 트렌드 분석 ({period} 단위)\n"]
        header = "| 기간 | " + " | ".join(valid_cols) + " | " + " | ".join([f"{c} 증감률(%)" for c in valid_cols]) + " |"
        sep = "|------|" + "------|" * len(valid_cols) * 2
        lines.append(header)
        lines.append(sep)

        for i, (idx, row) in enumerate(agg.iterrows()):
            period_str = str(idx)[:10]
            vals = [f"{row[c]:,.2f}" for c in valid_cols]
            if i == 0:
                changes = ["—"] * len(valid_cols)
            else:
                prev = agg.iloc[i - 1]
                changes = []
                for c in valid_cols:
                    if prev[c] != 0:
                        changes.append(f"{(row[c] - prev[c]) / abs(prev[c]) * 100:+.1f}%")
                    else:
                        changes.append("N/A")
            lines.append(f"| {period_str} | " + " | ".join(vals) + " | " + " | ".join(changes) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 트렌드 분석 실패: {e}"


def correlation_analysis(conn_id: str, sql: str, columns: list = None) -> str:
    """
    수치형 컬럼 간 Pearson 상관계수 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        columns: 분석할 컬럼 목록 (None이면 수치형 전체)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    num_df = df.select_dtypes(include="number")
    if columns:
        valid = [c for c in columns if c in num_df.columns]
        if not valid:
            return f"[ERROR] 지정한 columns 중 수치형 컬럼이 없습니다: {columns}"
        num_df = num_df[valid]

    if num_df.empty or len(num_df.columns) < 2:
        return "[ERROR] 상관관계 분석에는 수치형 컬럼이 2개 이상 필요합니다."

    try:
        corr = num_df.corr()
        cols = list(corr.columns)

        lines = ["## 상관관계 분석 (Pearson)\n"]
        header = "| 컬럼 | " + " | ".join(cols) + " |"
        sep = "|------|" + "------|" * len(cols)
        lines.append(header)
        lines.append(sep)
        for col in cols:
            vals = [f"{corr.loc[col, c]:.3f}" for c in cols]
            lines.append(f"| {col} | " + " | ".join(vals) + " |")

        strong = []
        for i, c1 in enumerate(cols):
            for c2 in cols[i+1:]:
                r = corr.loc[c1, c2]
                if abs(r) >= 0.7:
                    direction = "양의" if r > 0 else "음의"
                    strong.append(f"- **{c1}** ↔ **{c2}**: {direction} 강한 상관관계 (r={r:.3f})")

        if strong:
            lines.append("\n### 강한 상관관계 (|r| ≥ 0.7)")
            lines.extend(strong)
        else:
            lines.append("\n강한 상관관계(|r| ≥ 0.7)는 발견되지 않았습니다.")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 상관관계 분석 실패: {e}"


def distribution_analysis(conn_id: str, sql: str, column: str, bins: int = 10) -> str:
    """
    수치형 컬럼의 분포 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        column: 분석할 수치형 컬럼명
        bins: 구간(bucket) 수
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if column not in df.columns:
        return f"[ERROR] column '{column}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[column].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{column}'은 수치형 컬럼이 아닙니다."

        desc = s.describe(percentiles=[0.25, 0.5, 0.75, 0.90, 0.95])

        lines = [f"## 분포 분석: {column} (n={len(s):,})\n"]
        lines.append("| 통계 | 값 |")
        lines.append("|------|-----|")
        stat_labels = {"count": "데이터 수", "mean": "평균", "std": "표준편차",
                       "min": "최솟값", "25%": "1사분위(p25)", "50%": "중앙값(p50)",
                       "75%": "3사분위(p75)", "90%": "p90", "95%": "p95", "max": "최댓값"}
        for key, label in stat_labels.items():
            if key in desc.index:
                lines.append(f"| {label} | {desc[key]:,.4f} |")

        lines.append(f"\n### 구간 분포 (bins={bins})\n")
        lines.append("| 구간 | 건수 | 비율(%) |")
        lines.append("|------|------|---------|")
        counts, edges = pd.cut(s, bins=bins, retbins=True)
        bucket_counts = counts.value_counts().sort_index()
        total = len(s)
        for interval, cnt in bucket_counts.items():
            label = f"{interval.left:.2f} ~ {interval.right:.2f}"
            pct = cnt / total * 100
            lines.append(f"| {label} | {cnt:,} | {pct:.1f}% |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 분포 분석 실패: {e}"


def segment_analysis(conn_id: str, sql: str, group_col: str, metric_col: str, agg: str = "sum") -> str:
    """
    세그먼트별 집계 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: 그룹화 기준 컬럼
        metric_col: 집계할 수치형 컬럼
        agg: "sum"|"avg"|"count"|"min"|"max"
    """
    agg_map = {"sum": "sum", "avg": "mean", "count": "count", "min": "min", "max": "max"}
    if agg not in agg_map:
        return f"[ERROR] agg '{agg}'은 지원하지 않습니다. 사용 가능: {list(agg_map.keys())}"

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if group_col not in df.columns:
        return f"[ERROR] group_col '{group_col}'이 데이터에 없습니다."
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다."

    try:
        grouped = df.groupby(group_col)[metric_col].agg(agg_map[agg]).reset_index()
        grouped.columns = [group_col, metric_col]
        grouped = grouped.sort_values(metric_col, ascending=False)
        total = grouped[metric_col].sum()
        grouped["비율(%)"] = (grouped[metric_col] / total * 100).round(1) if total != 0 else 0

        lines = [f"## 세그먼트 분석: {group_col} 기준 {metric_col} ({agg})\n"]
        lines.append(f"| {group_col} | {metric_col} | 비율(%) |")
        lines.append("|------|------|---------|")
        for _, row in grouped.iterrows():
            lines.append(f"| {row[group_col]} | {row[metric_col]:,.2f} | {row['비율(%)']:.1f}% |")
        lines.append(f"\n**합계**: {total:,.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 세그먼트 분석 실패: {e}"


def funnel_analysis(conn_id: str, steps: list) -> str:
    """
    단계별 퍼널 전환율 분석.
    Args:
        conn_id: DB 연결 ID
        steps: [{"name": str, "sql": str}, ...] 각 SQL이 단계별 사용자/이벤트 수를 반환
    """
    if not steps:
        return "[ERROR] steps가 비어 있습니다."

    results = []
    for step in steps:
        name = step.get("name", "")
        sql = step.get("sql", "")
        df, err = _fetch_df(conn_id, sql)
        if err:
            return f"[ERROR] 단계 '{name}' 실행 실패: {err}"
        if df.empty:
            results.append((name, 0))
        else:
            val = df.iloc[0, 0]
            try:
                results.append((name, float(val)))
            except (TypeError, ValueError):
                results.append((name, 0))

    lines = ["## 퍼널 분석\n"]
    lines.append("| 단계 | 수치 | 전환율(%) | 누적 전환율(%) |")
    lines.append("|------|------|-----------|----------------|")

    first_val = results[0][1] if results else 0
    for i, (name, val) in enumerate(results):
        if i == 0:
            conv = "—"
            cumul = "100.0%"
        else:
            prev_val = results[i - 1][1]
            conv = f"{val / prev_val * 100:.1f}%" if prev_val else "N/A"
            cumul = f"{val / first_val * 100:.1f}%" if first_val else "N/A"
        lines.append(f"| {name} | {val:,.0f} | {conv} | {cumul} |")

    return "\n".join(lines)


def cohort_analysis(conn_id: str, sql: str, user_col: str, cohort_date_col: str, activity_date_col: str) -> str:
    """
    월별 코호트 리텐션 분석.
    Args:
        conn_id: DB 연결 ID
        sql: user_col, cohort_date_col, activity_date_col 포함 SQL
        user_col: 사용자 식별 컬럼
        cohort_date_col: 코호트 기준 날짜 컬럼 (첫 방문/가입일 등)
        activity_date_col: 활동 날짜 컬럼
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [user_col, cohort_date_col, activity_date_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[cohort_date_col] = pd.to_datetime(df[cohort_date_col])
        df[activity_date_col] = pd.to_datetime(df[activity_date_col])
        df["cohort_month"] = df[cohort_date_col].dt.to_period("M")
        df["activity_month"] = df[activity_date_col].dt.to_period("M")
        df["period"] = (df["activity_month"] - df["cohort_month"]).apply(lambda x: x.n if hasattr(x, "n") else 0)
        df = df[df["period"] >= 0]

        cohort_sizes = df[df["period"] == 0].groupby("cohort_month")[user_col].nunique()
        retention = df.groupby(["cohort_month", "period"])[user_col].nunique().unstack(fill_value=0)

        lines = ["## 코호트 리텐션 분석 (월 단위)\n"]
        periods = sorted(retention.columns)
        period_headers = " | ".join([f"M+{p}" for p in periods])
        lines.append(f"| 코호트 | 코호트 크기 | {period_headers} |")
        lines.append("|--------|------------|" + "---------|" * len(periods))

        for cohort, size in cohort_sizes.items():
            row_vals = []
            for p in periods:
                if p in retention.columns and cohort in retention.index:
                    cnt = retention.loc[cohort, p]
                    pct = cnt / size * 100 if size > 0 else 0
                    row_vals.append(f"{pct:.0f}%")
                else:
                    row_vals.append("—")
            lines.append(f"| {cohort} | {size:,} | " + " | ".join(row_vals) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 코호트 분석 실패: {e}"


def pivot_table(conn_id: str, sql: str, index_col: str, columns_col: str, values_col: str, aggfunc: str = "sum") -> str:
    """
    피벗 테이블 생성.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        index_col: 행 인덱스 컬럼
        columns_col: 열 헤더 컬럼
        values_col: 집계할 값 컬럼
        aggfunc: "sum"|"mean"|"count"|"min"|"max"
    """
    agg_map = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max"}
    if aggfunc not in agg_map:
        return f"[ERROR] aggfunc '{aggfunc}'은 지원하지 않습니다."

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in [index_col, columns_col, values_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        pivot = pd.pivot_table(df, values=values_col, index=index_col,
                               columns=columns_col, aggfunc=agg_map[aggfunc], fill_value=0)

        cols = list(pivot.columns)
        lines = [f"## 피벗 테이블: {index_col} × {columns_col} ({values_col}, {aggfunc})\n"]
        lines.append(f"| {index_col} | " + " | ".join([str(c) for c in cols]) + " |")
        lines.append("|------|" + "------|" * len(cols))
        for idx, row in pivot.iterrows():
            vals = [f"{row[c]:,.2f}" for c in cols]
            lines.append(f"| {idx} | " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 피벗 테이블 생성 실패: {e}"


def top_n_analysis(conn_id: str, sql: str, metric_col: str, n: int = 10, group_col: str = None) -> str:
    """
    Top-N 랭킹 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        metric_col: 내림차순 정렬 기준 수치형 컬럼
        n: 상위 N개
        group_col: 그룹별 Top-N (None이면 전체 Top-N)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        if group_col:
            if group_col not in df.columns:
                return f"[ERROR] group_col '{group_col}'이 데이터에 없습니다."
            result = df.groupby(group_col).apply(
                lambda g: g.nlargest(n, metric_col)
            ).reset_index(drop=True)
        else:
            result = df.nlargest(n, metric_col).copy()

        total = df[metric_col].sum()
        result["누적비율(%)"] = (result[metric_col].cumsum() / total * 100).round(1) if total else 0

        lines = [f"## Top-{n} 분석: {metric_col}" + (f" (by {group_col})" if group_col else "") + "\n"]
        display_cols = ([group_col] if group_col else []) + list(df.columns) + ["누적비율(%)"]
        display_cols = list(dict.fromkeys([c for c in display_cols if c in result.columns or c == "누적비율(%)"]))

        lines.append("| " + " | ".join(display_cols) + " |")
        lines.append("|" + "------|" * len(display_cols))
        for _, row in result.iterrows():
            vals = []
            for c in display_cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}")
                else:
                    vals.append(str(v))
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] Top-N 분석 실패: {e}"
