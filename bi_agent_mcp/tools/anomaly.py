"""이상치 탐지 도구 — iqr_anomaly_detection, zscore_anomaly_detection."""
import logging
import pandas as pd
import numpy as np
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


def iqr_anomaly_detection(
    conn_id: str,
    sql: str,
    metric_col: str,
    group_col: Optional[str] = None,
    multiplier: float = 1.5,
) -> str:
    """
    IQR(사분위 범위) 기반 이상치 탐지.
    Q1 - multiplier*IQR ~ Q3 + multiplier*IQR 범위를 벗어난 값을 이상치로 판별.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        metric_col: 이상치를 탐지할 수치형 컬럼명
        group_col: 그룹별 IQR 계산 기준 컬럼 (None이면 전체 기준)
        multiplier: IQR 배수 (기본 1.5)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    if group_col is not None and group_col not in df.columns:
        return f"[ERROR] group_col '{group_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[metric_col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{metric_col}'은 수치형 컬럼이 아닙니다."

        min_rows = 4
        if len(s) < min_rows:
            return f"[ERROR] IQR 이상치 탐지에는 최소 {min_rows}행이 필요합니다. 현재: {len(s)}행"

        # 그룹별 또는 전체 기준으로 경계 계산
        if group_col:
            working = df[[group_col, metric_col]].dropna(subset=[metric_col]).copy()

            def _bounds(g):
                vals = g[metric_col]
                q1 = vals.quantile(0.25)
                q3 = vals.quantile(0.75)
                iqr = q3 - q1
                return pd.Series({
                    "lower": q1 - multiplier * iqr,
                    "upper": q3 + multiplier * iqr,
                    "q1": q1,
                    "q3": q3,
                    "iqr": iqr,
                })

            bounds_df = working.groupby(group_col).apply(_bounds, include_groups=False).reset_index()
            working = working.merge(bounds_df, on=group_col, how="left")
        else:
            working = df[[metric_col]].dropna().copy()
            q1 = working[metric_col].quantile(0.25)
            q3 = working[metric_col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr
            working["lower"] = lower
            working["upper"] = upper
            working["q1"] = q1
            working["q3"] = q3
            working["iqr"] = iqr

        anomalies = working[
            (working[metric_col] < working["lower"]) |
            (working[metric_col] > working["upper"])
        ].copy()

        total = len(working)
        n_anomaly = len(anomalies)
        ratio = n_anomaly / total * 100 if total > 0 else 0.0

        lines = [f"## IQR 이상치 탐지: {metric_col} (multiplier={multiplier})\n"]

        # 요약
        lines.append("### 요약")
        lines.append(f"- 전체 데이터: {total:,}행")
        lines.append(f"- 이상치 수: {n_anomaly:,}개")
        lines.append(f"- 이상치 비율: {ratio:.2f}%\n")

        # 정상 범위 정보
        if group_col:
            lines.append("### 그룹별 정상 범위")
            lines.append(f"| {group_col} | Q1 | Q3 | IQR | 하한 | 상한 |")
            lines.append("|------|------|------|------|------|------|")
            for _, brow in bounds_df.iterrows():
                lines.append(
                    f"| {brow[group_col]} | {brow['q1']:,.4f} | {brow['q3']:,.4f} | "
                    f"{brow['iqr']:,.4f} | {brow['lower']:,.4f} | {brow['upper']:,.4f} |"
                )
        else:
            lines.append("### 정상 범위")
            lines.append(f"- Q1: {q1:,.4f}")
            lines.append(f"- Q3: {q3:,.4f}")
            lines.append(f"- IQR: {iqr:,.4f}")
            lines.append(f"- 하한 (Q1 - {multiplier}×IQR): {lower:,.4f}")
            lines.append(f"- 상한 (Q3 + {multiplier}×IQR): {upper:,.4f}\n")

        # 이상치 목록
        if n_anomaly == 0:
            lines.append("\n이상치가 발견되지 않았습니다.")
        else:
            lines.append("\n### 이상치 목록")
            header_cols = ([group_col] if group_col else []) + [metric_col, "하한", "상한", "방향", "이상치 정도"]
            lines.append("| " + " | ".join(header_cols) + " |")
            lines.append("|" + "------|" * len(header_cols))

            for _, row in anomalies.iterrows():
                direction = "상향" if row[metric_col] > row["upper"] else "하향"
                boundary = row["upper"] if direction == "상향" else row["lower"]
                degree = abs(row[metric_col] - boundary)
                parts = []
                if group_col:
                    parts.append(str(row[group_col]))
                parts += [
                    f"{row[metric_col]:,.4f}",
                    f"{row['lower']:,.4f}",
                    f"{row['upper']:,.4f}",
                    direction,
                    f"{degree:,.4f}",
                ]
                lines.append("| " + " | ".join(parts) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] IQR 이상치 탐지 실패: {e}"


def zscore_anomaly_detection(
    conn_id: str,
    sql: str,
    metric_col: str,
    threshold: float = 3.0,
    time_col: Optional[str] = None,
    period: Optional[str] = None,
) -> str:
    """
    Z-Score 기반 이상치 탐지.
    |Z| > threshold인 값을 이상치로 판별 (기본 threshold=3.0, 3σ 기준).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        metric_col: 이상치를 탐지할 수치형 컬럼명
        threshold: Z-score 임계값 (기본 3.0)
        time_col: 시계열 컨텍스트용 날짜/시간 컬럼 (선택)
        period: "day"|"week"|"month"|"quarter"|"year" (time_col과 함께 사용)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    if time_col is not None and time_col not in df.columns:
        return f"[ERROR] time_col '{time_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[metric_col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{metric_col}'은 수치형 컬럼이 아닙니다."

        min_rows = 3
        if len(s) < min_rows:
            return f"[ERROR] Z-Score 이상치 탐지에는 최소 {min_rows}행이 필요합니다. 현재: {len(s)}행"

        mean = float(s.mean())
        std = float(s.std(ddof=1))

        if std == 0:
            return f"[ERROR] '{metric_col}'의 표준편차가 0입니다. Z-Score 계산이 불가능합니다."

        working = df[[metric_col] + ([time_col] if time_col else [])].dropna(subset=[metric_col]).copy()
        working["_zscore"] = (working[metric_col] - mean) / std
        working["_abs_z"] = working["_zscore"].abs()

        anomalies = working[working["_abs_z"] > threshold].copy()

        total = len(working)
        n_anomaly = len(anomalies)
        ratio = n_anomaly / total * 100 if total > 0 else 0.0

        z_min = float(working["_zscore"].min())
        z_max = float(working["_zscore"].max())
        z_mean = float(working["_zscore"].mean())

        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

        lines = [f"## Z-Score 이상치 탐지: {metric_col} (threshold=|Z|>{threshold})\n"]

        # 요약
        lines.append("### 요약")
        lines.append(f"- 전체 데이터: {total:,}행")
        lines.append(f"- 이상치 수: {n_anomaly:,}개")
        lines.append(f"- 이상치 비율: {ratio:.2f}%")
        lines.append(f"- 평균: {mean:,.4f}, 표준편차: {std:,.4f}")
        lines.append(f"- Z-Score 분포 — 최솟값: {z_min:.4f}, 최댓값: {z_max:.4f}, 평균: {z_mean:.4f}")
        lines.append(f"- 정상 범위: {lower_bound:,.4f} ~ {upper_bound:,.4f}\n")

        # 심각도 분류
        if n_anomaly > 0:
            warn = anomalies[(anomalies["_abs_z"] >= threshold) & (anomalies["_abs_z"] < 4.0)]
            severe = anomalies[(anomalies["_abs_z"] >= 4.0) & (anomalies["_abs_z"] < 5.0)]
            critical = anomalies[anomalies["_abs_z"] >= 5.0]

            lines.append("### 심각도 분류")
            lines.append(f"- 경고 ({threshold:.1f}≤|Z|<4): {len(warn):,}개")
            lines.append(f"- 심각 (4≤|Z|<5): {len(severe):,}개")
            lines.append(f"- 위험 (|Z|≥5): {len(critical):,}개\n")

        # 시계열 컨텍스트 (기간별 이상치 분포)
        if time_col and period and n_anomaly > 0:
            period_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
            if period not in period_map:
                lines.append(f"[경고] period '{period}'은 지원하지 않습니다. 시계열 분석을 건너뜁니다.\n")
            else:
                try:
                    anomalies_ts = anomalies.copy()
                    anomalies_ts[time_col] = pd.to_datetime(anomalies_ts[time_col])
                    anomalies_ts = anomalies_ts.set_index(time_col)
                    period_counts = anomalies_ts["_zscore"].resample(period_map[period]).count()
                    period_counts = period_counts[period_counts > 0]

                    lines.append(f"### 기간별 이상치 분포 ({period} 단위)")
                    lines.append("| 기간 | 이상치 수 |")
                    lines.append("|------|-----------|")
                    for idx, cnt in period_counts.items():
                        lines.append(f"| {str(idx)[:10]} | {cnt:,} |")
                    lines.append("")
                except Exception:
                    pass  # 시계열 파싱 실패 시 건너뜀

        # 이상치 목록
        if n_anomaly == 0:
            lines.append("이상치가 발견되지 않았습니다.")
        else:
            lines.append("### 이상치 목록")
            header_cols = ([time_col] if time_col else []) + [metric_col, "Z-Score", "정상범위 하한", "정상범위 상한", "심각도"]
            lines.append("| " + " | ".join(header_cols) + " |")
            lines.append("|" + "------|" * len(header_cols))

            for _, row in anomalies.sort_values("_abs_z", ascending=False).iterrows():
                abs_z = row["_abs_z"]
                if abs_z >= 5.0:
                    severity = "위험"
                elif abs_z >= 4.0:
                    severity = "심각"
                else:
                    severity = "경고"
                parts = []
                if time_col:
                    parts.append(str(row[time_col]))
                parts += [
                    f"{row[metric_col]:,.4f}",
                    f"{row['_zscore']:+.4f}",
                    f"{lower_bound:,.4f}",
                    f"{upper_bound:,.4f}",
                    severity,
                ]
                lines.append("| " + " | ".join(parts) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] Z-Score 이상치 탐지 실패: {e}"
