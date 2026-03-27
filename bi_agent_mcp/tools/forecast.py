"""시계열 예측 도구 — moving_average_forecast, exponential_smoothing_forecast, linear_trend_forecast."""
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


_PERIOD_MAP = {
    "day": "D",
    "week": "W",
    "month": "ME",
    "quarter": "QE",
    "year": "YE",
}

_PERIOD_OFFSETS = {
    "day": pd.DateOffset(days=1),
    "week": pd.DateOffset(weeks=1),
    "month": pd.DateOffset(months=1),
    "quarter": pd.DateOffset(months=3),
    "year": pd.DateOffset(years=1),
}


def _aggregate_series(df: pd.DataFrame, time_col: str, metric_col: str, period: str):
    """time_col 기준으로 period 단위 집계 후 Series 반환."""
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    agg = df[[metric_col]].resample(_PERIOD_MAP[period]).sum()
    return agg[metric_col].dropna()


def moving_average_forecast(
    conn_id: str,
    sql: str,
    time_col: str,
    metric_col: str,
    window: int = 3,
    forecast_periods: int = 3,
    period: str = "month",
) -> str:
    """[Forecast] 이동평균(SMA) 기반 예측.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        time_col: 날짜/시간 컬럼명
        metric_col: 예측할 수치형 컬럼명
        window: 이동평균 기간 수
        forecast_periods: 미래 예측 기간 수
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    if period not in _PERIOD_MAP:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(_PERIOD_MAP.keys())}"
    if window < 1:
        return "[ERROR] window는 1 이상이어야 합니다."
    if forecast_periods < 1:
        return "[ERROR] forecast_periods는 1 이상이어야 합니다."

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if time_col not in df.columns:
        return f"[ERROR] time_col '{time_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    min_rows = window * 2
    try:
        series = _aggregate_series(df, time_col, metric_col, period)
    except Exception as e:
        return f"[ERROR] 데이터 집계 실패: {e}"

    if len(series) < min_rows:
        return f"[ERROR] 데이터가 부족합니다. 이동평균(window={window}) 예측에는 최소 {min_rows}개 기간이 필요하지만 {len(series)}개만 있습니다."

    try:
        ma = series.rolling(window=window).mean()

        lines = [f"## 이동평균 예측 (window={window}, {period} 단위)\n"]
        lines.append(f"| 기간 | 실제값 | 이동평균(SMA-{window}) |")
        lines.append("|------|--------|----------------------|")
        for idx, val in series.items():
            ma_val = ma[idx]
            ma_str = f"{ma_val:,.2f}" if not np.isnan(ma_val) else "—"
            lines.append(f"| {str(idx)[:10]} | {val:,.2f} | {ma_str} |")

        # 예측: 마지막 window 값의 평균을 반복 적용
        last_values = list(series.values[-window:])
        last_idx = series.index[-1]
        offset = _PERIOD_OFFSETS[period]

        lines.append(f"\n### 미래 예측 ({forecast_periods}기간)\n")
        lines.append("| 예측 기간 | 예측값 |")
        lines.append("|-----------|--------|")
        for i in range(forecast_periods):
            forecast_idx = last_idx + offset * (i + 1)
            forecast_val = np.mean(last_values[-window:])
            last_values.append(forecast_val)
            lines.append(f"| {str(forecast_idx)[:10]} | {forecast_val:,.2f} |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 이동평균 예측 실패: {e}"


def exponential_smoothing_forecast(
    conn_id: str,
    sql: str,
    time_col: str,
    metric_col: str,
    alpha: float = 0.3,
    forecast_periods: int = 3,
    period: str = "month",
) -> str:
    """[Forecast] 지수평활(Exponential Smoothing) 기반 예측 (외부 라이브러리 없이 순수 pandas/numpy).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        time_col: 날짜/시간 컬럼명
        metric_col: 예측할 수치형 컬럼명
        alpha: 평활 계수 (0~1, 높을수록 최근값 반영)
        forecast_periods: 미래 예측 기간 수
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    if period not in _PERIOD_MAP:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(_PERIOD_MAP.keys())}"
    if not (0 < alpha <= 1):
        return f"[ERROR] alpha는 0 초과 1 이하여야 합니다. 입력값: {alpha}"
    if forecast_periods < 1:
        return "[ERROR] forecast_periods는 1 이상이어야 합니다."

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if time_col not in df.columns:
        return f"[ERROR] time_col '{time_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        series = _aggregate_series(df, time_col, metric_col, period)
    except Exception as e:
        return f"[ERROR] 데이터 집계 실패: {e}"

    if len(series) < 2:
        return f"[ERROR] 지수평활 예측에는 최소 2개 기간이 필요하지만 {len(series)}개만 있습니다."

    try:
        values = series.values.astype(float)
        smoothed = np.empty(len(values))
        smoothed[0] = values[0]
        for i in range(1, len(values)):
            smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i - 1]

        # MAPE 계산 (0이 아닌 실제값에 대해서만)
        nonzero_mask = values != 0
        if nonzero_mask.any():
            mape = np.mean(np.abs((values[nonzero_mask] - smoothed[nonzero_mask]) / values[nonzero_mask])) * 100
            mape_str = f"{mape:.2f}%"
        else:
            mape_str = "N/A"

        lines = [f"## 지수평활 예측 (alpha={alpha}, {period} 단위)\n"]
        lines.append(f"| 기간 | 실제값 | 평활값 |")
        lines.append("|------|--------|--------|")
        for idx, (val, s_val) in zip(series.index, zip(values, smoothed)):
            lines.append(f"| {str(idx)[:10]} | {val:,.2f} | {s_val:,.2f} |")

        last_smoothed = smoothed[-1]
        last_idx = series.index[-1]
        offset = _PERIOD_OFFSETS[period]

        lines.append(f"\n### 미래 예측 ({forecast_periods}기간)\n")
        lines.append("| 예측 기간 | 예측값 |")
        lines.append("|-----------|--------|")
        # 지수평활에서 미래 예측값은 마지막 평활값과 동일 (단순 평활)
        for i in range(forecast_periods):
            forecast_idx = last_idx + offset * (i + 1)
            lines.append(f"| {str(forecast_idx)[:10]} | {last_smoothed:,.2f} |")

        lines.append(f"\n**MAPE (평균절대백분율오차)**: {mape_str}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 지수평활 예측 실패: {e}"


def linear_trend_forecast(
    conn_id: str,
    sql: str,
    time_col: str,
    metric_col: str,
    forecast_periods: int = 3,
    period: str = "month",
) -> str:
    """[Forecast] 선형 회귀(OLS) 기반 트렌드 예측 (numpy.polyfit 사용).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        time_col: 날짜/시간 컬럼명
        metric_col: 예측할 수치형 컬럼명
        forecast_periods: 미래 예측 기간 수
        period: "day"|"week"|"month"|"quarter"|"year"
    """
    if period not in _PERIOD_MAP:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(_PERIOD_MAP.keys())}"
    if forecast_periods < 1:
        return "[ERROR] forecast_periods는 1 이상이어야 합니다."

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if time_col not in df.columns:
        return f"[ERROR] time_col '{time_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        series = _aggregate_series(df, time_col, metric_col, period)
    except Exception as e:
        return f"[ERROR] 데이터 집계 실패: {e}"

    if len(series) < 3:
        return f"[ERROR] 선형 추세 예측에는 최소 3개 기간이 필요하지만 {len(series)}개만 있습니다."

    try:
        x = np.arange(len(series), dtype=float)
        y = series.values.astype(float)

        coeffs = np.polyfit(x, y, deg=1)
        slope = coeffs[0]
        intercept = coeffs[1]

        trend_line = np.polyval(coeffs, x)

        # R² 계산
        ss_res = np.sum((y - trend_line) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0

        lines = [f"## 선형 추세 예측 ({period} 단위)\n"]
        lines.append("| 기간 | 실제값 | 추세선 |")
        lines.append("|------|--------|--------|")
        for i, (idx, val) in enumerate(series.items()):
            lines.append(f"| {str(idx)[:10]} | {val:,.2f} | {trend_line[i]:,.2f} |")

        last_idx = series.index[-1]
        offset = _PERIOD_OFFSETS[period]
        n = len(series)

        lines.append(f"\n### 미래 예측 ({forecast_periods}기간)\n")
        lines.append("| 예측 기간 | 예측값 |")
        lines.append("|-----------|--------|")
        for i in range(forecast_periods):
            forecast_x = n + i
            forecast_val = np.polyval(coeffs, forecast_x)
            forecast_idx = last_idx + offset * (i + 1)
            lines.append(f"| {str(forecast_idx)[:10]} | {forecast_val:,.2f} |")

        # 성장률 (기울기를 평균값 대비 퍼센트로)
        mean_val = np.mean(y)
        if mean_val != 0:
            growth_rate = slope / abs(mean_val) * 100
            growth_str = f"{growth_rate:+.2f}%/기간"
        else:
            growth_str = "N/A"

        lines.append(f"\n**R² (결정계수)**: {r2:.4f}")
        lines.append(f"**기울기 (성장률)**: {slope:,.4f} ({growth_str})")
        lines.append(f"**절편**: {intercept:,.4f}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 선형 추세 예측 실패: {e}"
