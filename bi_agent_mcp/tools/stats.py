"""통계 분석 도구 — 기술통계, 추론통계, 가설검정."""
from __future__ import annotations
import logging
import math
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select

# scipy optional dual-path
try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


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


def _p_from_t(t_stat: float, df: int, two_tailed: bool = True) -> float:
    """t-통계량에서 p-value 계산 (scipy 없을 때 정규근사 사용)."""
    if _HAS_SCIPY:
        p = float(_scipy_stats.t.sf(abs(t_stat), df))
        return p * 2 if two_tailed else p
    # 정규분포 근사 (df >= 30 권장)
    p = math.erfc(abs(t_stat) / math.sqrt(2))
    return p if two_tailed else p / 2


def _p_from_f(f_stat: float, df1: int, df2: int) -> float:
    """F-통계량에서 p-value 계산."""
    if _HAS_SCIPY:
        return float(_scipy_stats.f.sf(f_stat, df1, df2))
    # 근사: chi2 근사 사용
    chi2 = df1 * f_stat
    p = math.erfc(math.sqrt(chi2 / 2))
    return min(p, 1.0)


def _p_from_chi2(chi2_stat: float, df: int) -> float:
    """카이제곱 통계량에서 p-value 계산."""
    if _HAS_SCIPY:
        return float(_scipy_stats.chi2.sf(chi2_stat, df))
    # 근사
    p = math.erfc(math.sqrt(chi2_stat / 2))
    return min(p, 1.0)


def _significance(p: float, alpha: float = 0.05) -> str:
    """p-value → 유의성 판정 문자열."""
    if p < 0.001:
        return f"유의미한 차이 있음 (p < 0.001, ***)"
    elif p < 0.01:
        return f"유의미한 차이 있음 (p = {p:.4f}, **)"
    elif p < alpha:
        return f"유의미한 차이 있음 (p = {p:.4f}, *)"
    else:
        return f"유의미한 차이 없음 (p = {p:.4f})"


# ─────────────────────────────────────────────────────────────────────────────
# 기술통계 (3개)
# ─────────────────────────────────────────────────────────────────────────────

def descriptive_stats(conn_id: str, sql: str, columns: list = None) -> str:
    """[Statistics] 수치형 컬럼별 기술통계 분석.
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

    if num_df.empty:
        return "[ERROR] 수치형 컬럼이 없습니다."

    try:
        lines = ["## 기술통계 분석\n"]
        header = "| 컬럼 | n | 평균 | 중앙값 | 표준편차 | 분산 | 최솟값 | 최댓값 | 왜도 | 첨도 | p25 | p50 | p75 |"
        sep =    "|------|---|------|--------|----------|------|--------|--------|------|------|-----|-----|-----|"
        lines.append(header)
        lines.append(sep)

        for col in num_df.columns:
            s = num_df[col].dropna()
            n = len(s)
            if n == 0:
                lines.append(f"| {col} | 0 | — | — | — | — | — | — | — | — | — | — | — |")
                continue
            mean = float(s.mean())
            median = float(s.median())
            std = float(s.std())
            var = float(s.var())
            mn = float(s.min())
            mx = float(s.max())
            skew = float(s.skew())
            kurt = float(s.kurtosis())
            p25 = float(s.quantile(0.25))
            p50 = float(s.quantile(0.50))
            p75 = float(s.quantile(0.75))
            lines.append(
                f"| {col} | {n:,} | {mean:.4f} | {median:.4f} | {std:.4f} | {var:.4f} "
                f"| {mn:.4f} | {mx:.4f} | {skew:.4f} | {kurt:.4f} "
                f"| {p25:.4f} | {p50:.4f} | {p75:.4f} |"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 기술통계 분석 실패: {e}"


def percentile_analysis(conn_id: str, sql: str, col: str, percentiles: list = None) -> str:
    """[Statistics] 컬럼의 백분위수 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 분석할 수치형 컬럼명
        percentiles: 백분위수 목록 (기본값: [10, 25, 50, 75, 90, 95, 99])
    """
    if percentiles is None:
        percentiles = [10, 25, 50, 75, 90, 95, 99]

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{col}'은 수치형 컬럼이 아닙니다."
        n = len(s)
        if n == 0:
            return f"[ERROR] '{col}'에 유효한 데이터가 없습니다."

        lines = [f"## 백분위수 분석: {col} (n={n:,})\n"]
        lines.append("| 백분위수 | 값 | 해당 구간 데이터 수 | 비율(%) |")
        lines.append("|----------|-----|---------------------|---------|")

        pct_values = [float(s.quantile(p / 100)) for p in percentiles]

        for i, (p, pv) in enumerate(zip(percentiles, pct_values)):
            if i == 0:
                lower = float(s.min())
            else:
                lower = pct_values[i - 1]
            upper = pv
            if i == 0:
                cnt = int((s <= upper).sum())
            else:
                cnt = int(((s > lower) & (s <= upper)).sum())
            ratio = cnt / n * 100
            lines.append(f"| p{p} | {pv:.4f} | {cnt:,} | {ratio:.1f}% |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 백분위수 분석 실패: {e}"


def boxplot_summary(conn_id: str, sql: str, col: str, group_col: str = None) -> str:
    """[Statistics] 박스플롯 요약 통계 (IQR, 수염, 이상치).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 분석할 수치형 컬럼명
        group_col: 그룹별 계산할 컬럼 (None이면 전체)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if group_col and group_col not in df.columns:
        return f"[ERROR] group_col '{group_col}'이 데이터에 없습니다."

    try:
        def _box_stats(s: pd.Series, label: str) -> str:
            s = s.dropna()
            if len(s) == 0:
                return f"| {label} | — | — | — | — | — | — | — | — |"
            q1 = float(s.quantile(0.25))
            q2 = float(s.quantile(0.50))
            q3 = float(s.quantile(0.75))
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            lower_whisker = float(s[s >= lower_fence].min())
            upper_whisker = float(s[s <= upper_fence].max())
            outliers = int(((s < lower_fence) | (s > upper_fence)).sum())
            return (
                f"| {label} | {q1:.4f} | {q2:.4f} | {q3:.4f} | {iqr:.4f} "
                f"| {lower_whisker:.4f} | {upper_whisker:.4f} | {lower_fence:.4f}~{upper_fence:.4f} | {outliers:,} |"
            )

        lines = [f"## 박스플롯 요약: {col}" + (f" (그룹: {group_col})" if group_col else "") + "\n"]
        lines.append("| 그룹 | Q1 | 중앙값(Q2) | Q3 | IQR | 하한 수염 | 상한 수염 | 이상치 경계 | 이상치 수 |")
        lines.append("|------|-----|------------|-----|-----|-----------|-----------|-------------|-----------|")

        if group_col:
            for grp, gdf in df.groupby(group_col):
                lines.append(_box_stats(gdf[col], str(grp)))
        else:
            lines.append(_box_stats(df[col], "전체"))

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 박스플롯 요약 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 추론통계 (2개)
# ─────────────────────────────────────────────────────────────────────────────

def confidence_interval(conn_id: str, sql: str, col: str, confidence: float = 0.95) -> str:
    """[Statistics] 평균의 신뢰구간 계산.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 분석할 수치형 컬럼명
        confidence: 신뢰수준 (기본값: 0.95)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{col}'은 수치형 컬럼이 아닙니다."
        n = len(s)
        if n < 2:
            return f"[ERROR] 신뢰구간 계산에는 최소 2개 데이터가 필요합니다."

        mean = float(s.mean())
        std = float(s.std())
        se = std / math.sqrt(n)
        alpha = 1 - confidence

        if _HAS_SCIPY:
            t_crit = float(_scipy_stats.t.ppf(1 - alpha / 2, df=n - 1))
            method = "t-분포 (scipy)"
        else:
            # 정규분포 근사
            z_map = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
            t_crit = z_map.get(round(confidence, 2), 1.960)
            method = "정규분포 근사 (scipy 없음)"

        margin = t_crit * se
        lower = mean - margin
        upper = mean + margin

        lines = [f"## 신뢰구간 분석: {col}\n"]
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 표본 수 (n) | {n:,} |")
        lines.append(f"| 표본 평균 | {mean:.6f} |")
        lines.append(f"| 표본 표준편차 | {std:.6f} |")
        lines.append(f"| 표준오차 (SE) | {se:.6f} |")
        lines.append(f"| 신뢰수준 | {confidence*100:.0f}% |")
        lines.append(f"| 임계값 (t/z) | {t_crit:.4f} |")
        lines.append(f"| 오차 한계 | ±{margin:.6f} |")
        lines.append(f"| **신뢰구간** | **[{lower:.6f}, {upper:.6f}]** |")
        lines.append(f"| 계산 방법 | {method} |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 신뢰구간 계산 실패: {e}"


def sampling_error(conn_id: str, sql: str, col: str, confidence: float = 0.95) -> str:
    """[Statistics] 표본오차 및 필요 표본 수 계산.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 분석할 수치형 컬럼명
        confidence: 신뢰수준 (기본값: 0.95)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{col}'은 수치형 컬럼이 아닙니다."
        n = len(s)
        if n < 2:
            return f"[ERROR] 표본오차 계산에는 최소 2개 데이터가 필요합니다."

        std = float(s.std())
        se = std / math.sqrt(n)

        z_map = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
        if _HAS_SCIPY:
            z = float(_scipy_stats.norm.ppf(1 - (1 - confidence) / 2))
        else:
            z = z_map.get(round(confidence, 2), 1.960)

        error_margin = z * se
        n_needed = math.ceil((z * std / error_margin) ** 2) if error_margin > 0 else n

        lines = [f"## 표본오차 분석: {col}\n"]
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 현재 표본 수 (n) | {n:,} |")
        lines.append(f"| 표본 표준편차 | {std:.6f} |")
        lines.append(f"| 표준오차 (SE) | {se:.6f} |")
        lines.append(f"| 신뢰수준 | {confidence*100:.0f}% |")
        lines.append(f"| z-값 | {z:.4f} |")
        lines.append(f"| **표본오차 (E)** | **±{error_margin:.6f}** |")
        lines.append(f"| 동일 오차 유지를 위한 필요 표본 수 | {n_needed:,} |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 표본오차 계산 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 가설검정 (6개)
# ─────────────────────────────────────────────────────────────────────────────

def ttest_one_sample(conn_id: str, sql: str, col: str, mu: float) -> str:
    """[Statistics] 단일 표본 t-검정. H0: 모평균 = mu.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 검정할 수치형 컬럼명
        mu: 귀무가설 모평균 값
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{col}'은 수치형 컬럼이 아닙니다."
        n = len(s)
        if n < 2:
            return f"[ERROR] t-검정에는 최소 2개 데이터가 필요합니다."

        mean = float(s.mean())
        std = float(s.std())
        t_stat = (mean - mu) / (std / math.sqrt(n))
        df_val = n - 1
        p_val = _p_from_t(t_stat, df_val, two_tailed=True)

        lines = [f"## 단일 표본 t-검정: {col}\n"]
        lines.append(f"- **귀무가설 (H0)**: 모평균 = {mu}")
        lines.append(f"- **대립가설 (H1)**: 모평균 ≠ {mu}\n")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 표본 수 (n) | {n:,} |")
        lines.append(f"| 표본 평균 | {mean:.6f} |")
        lines.append(f"| 표본 표준편차 | {std:.6f} |")
        lines.append(f"| t-통계량 | {t_stat:.6f} |")
        lines.append(f"| 자유도 (df) | {df_val} |")
        lines.append(f"| p-value | {p_val:.6f} |")
        lines.append(f"\n**판정**: {_significance(p_val)}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 단일 표본 t-검정 실패: {e}"


def ttest_independent(conn_id: str, sql: str, group_col: str, value_col: str,
                      alternative: str = "two-sided") -> str:
    """[Statistics] 독립 표본 t-검정 (Welch's t-test, 등분산 가정 없음).
    두 그룹 간 평균 차이를 검정합니다.
    A/B 테스트 시나리오는 product.ab_test_analysis를 사용하세요.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: 그룹 구분 컬럼 (정확히 2개 고유값 필요)
        value_col: 검정할 수치형 컬럼명
        alternative: "two-sided"|"greater"|"less"
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    for c in [group_col, value_col]:
        if c not in df.columns:
            return f"[ERROR] column '{c}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        groups = df[group_col].dropna().unique()
        if len(groups) != 2:
            return f"[ERROR] group_col '{group_col}'은 정확히 2개 고유값이어야 합니다. 현재: {len(groups)}개"

        g1 = df[df[group_col] == groups[0]][value_col].dropna()
        g2 = df[df[group_col] == groups[1]][value_col].dropna()

        n1, n2 = len(g1), len(g2)
        if n1 < 2 or n2 < 2:
            return "[ERROR] 각 그룹에 최소 2개 데이터가 필요합니다."

        m1, m2 = float(g1.mean()), float(g2.mean())
        s1, s2 = float(g1.std()), float(g2.std())
        v1, v2 = s1 ** 2 / n1, s2 ** 2 / n2

        t_stat = (m1 - m2) / math.sqrt(v1 + v2)
        # Welch-Satterthwaite df
        df_w = (v1 + v2) ** 2 / ((v1 ** 2 / (n1 - 1)) + (v2 ** 2 / (n2 - 1)))
        df_val = int(df_w)

        two_tailed = alternative == "two-sided"
        p_val = _p_from_t(t_stat, df_val, two_tailed=two_tailed)
        if alternative == "greater":
            p_val = p_val / 2 if t_stat > 0 else 1 - p_val / 2
        elif alternative == "less":
            p_val = p_val / 2 if t_stat < 0 else 1 - p_val / 2

        lines = [f"## 독립 표본 t-검정 (Welch): {value_col} by {group_col}\n"]
        lines.append(f"- **그룹 A**: {groups[0]}  |  **그룹 B**: {groups[1]}")
        lines.append(f"- **대립가설**: {alternative}\n")
        lines.append("| 항목 | 그룹 A | 그룹 B |")
        lines.append("|------|--------|--------|")
        lines.append(f"| 표본 수 | {n1:,} | {n2:,} |")
        lines.append(f"| 평균 | {m1:.6f} | {m2:.6f} |")
        lines.append(f"| 표준편차 | {s1:.6f} | {s2:.6f} |")
        lines.append("\n| 검정 통계 | 값 |")
        lines.append("|-----------|-----|")
        lines.append(f"| t-통계량 | {t_stat:.6f} |")
        lines.append(f"| 자유도 (Welch df) | {df_val} |")
        lines.append(f"| p-value | {p_val:.6f} |")
        lines.append(f"\n**판정**: {_significance(p_val)}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 독립 표본 t-검정 실패: {e}"


def ttest_paired(conn_id: str, sql: str, col_a: str, col_b: str) -> str:
    """[Statistics] 대응 표본 t-검정. H0: mean(col_a - col_b) = 0.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col_a: 첫 번째 측정값 컬럼
        col_b: 두 번째 측정값 컬럼
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    for c in [col_a, col_b]:
        if c not in df.columns:
            return f"[ERROR] column '{c}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        pair_df = df[[col_a, col_b]].dropna()
        n = len(pair_df)
        if n < 2:
            return "[ERROR] 대응 표본 t-검정에는 최소 2쌍의 데이터가 필요합니다."

        d = pair_df[col_a] - pair_df[col_b]
        mean_d = float(d.mean())
        std_d = float(d.std())
        t_stat = mean_d / (std_d / math.sqrt(n))
        df_val = n - 1
        p_val = _p_from_t(t_stat, df_val, two_tailed=True)

        lines = [f"## 대응 표본 t-검정: {col_a} vs {col_b}\n"]
        lines.append(f"- **귀무가설 (H0)**: mean({col_a} - {col_b}) = 0\n")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 쌍 수 (n) | {n:,} |")
        lines.append(f"| 차이의 평균 | {mean_d:.6f} |")
        lines.append(f"| 차이의 표준편차 | {std_d:.6f} |")
        lines.append(f"| t-통계량 | {t_stat:.6f} |")
        lines.append(f"| 자유도 (df) | {df_val} |")
        lines.append(f"| p-value | {p_val:.6f} |")
        lines.append(f"\n**판정**: {_significance(p_val)}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 대응 표본 t-검정 실패: {e}"


def anova_one_way(conn_id: str, sql: str, group_col: str, value_col: str) -> str:
    """[Statistics] 일원 분산분석 (One-Way ANOVA).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: 그룹 구분 컬럼
        value_col: 검정할 수치형 컬럼명
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    for c in [group_col, value_col]:
        if c not in df.columns:
            return f"[ERROR] column '{c}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df = df[[group_col, value_col]].dropna()
        groups = df[group_col].unique()
        k = len(groups)
        if k < 2:
            return f"[ERROR] ANOVA에는 최소 2개 그룹이 필요합니다. 현재: {k}개"

        N = len(df)
        grand_mean = float(df[value_col].mean())

        group_data = {g: df[df[group_col] == g][value_col].values for g in groups}
        group_ns = {g: len(v) for g, v in group_data.items()}
        group_means = {g: float(v.mean()) for g, v in group_data.items()}
        group_stds = {g: float(v.std()) for g, v in group_data.items()}

        ss_between = sum(group_ns[g] * (group_means[g] - grand_mean) ** 2 for g in groups)
        ss_within = sum(float(np.sum((v - group_means[g]) ** 2)) for g, v in group_data.items())

        df1 = k - 1
        df2 = N - k
        if df2 <= 0:
            return "[ERROR] 자유도가 부족합니다. 각 그룹에 더 많은 데이터가 필요합니다."

        msb = ss_between / df1
        msw = ss_within / df2
        f_stat = msb / msw if msw > 0 else float("inf")
        p_val = _p_from_f(f_stat, df1, df2)

        lines = [f"## 일원 분산분석 (ANOVA): {value_col} by {group_col}\n"]
        lines.append("### 그룹별 통계\n")
        lines.append(f"| {group_col} | n | 평균 | 표준편차 |")
        lines.append("|------|---|------|----------|")
        for g in groups:
            lines.append(f"| {g} | {group_ns[g]:,} | {group_means[g]:.6f} | {group_stds[g]:.6f} |")

        lines.append("\n### ANOVA 결과\n")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 전체 표본 수 (N) | {N:,} |")
        lines.append(f"| 그룹 수 (k) | {k} |")
        lines.append(f"| SS_between | {ss_between:.6f} |")
        lines.append(f"| SS_within | {ss_within:.6f} |")
        lines.append(f"| MS_between | {msb:.6f} |")
        lines.append(f"| MS_within | {msw:.6f} |")
        lines.append(f"| F-통계량 | {f_stat:.6f} |")
        lines.append(f"| 자유도 (df1, df2) | ({df1}, {df2}) |")
        lines.append(f"| p-value | {p_val:.6f} |")
        lines.append(f"\n**판정**: {_significance(p_val)}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 일원 분산분석 실패: {e}"


def chi_square_test(conn_id: str, sql: str, col_a: str, col_b: str) -> str:
    """[Statistics] 카이제곱 독립성 검정.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col_a: 첫 번째 범주형 컬럼
        col_b: 두 번째 범주형 컬럼
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    for c in [col_a, col_b]:
        if c not in df.columns:
            return f"[ERROR] column '{c}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df = df[[col_a, col_b]].dropna()
        contingency = pd.crosstab(df[col_a], df[col_b])
        rows = list(contingency.index)
        cols = list(contingency.columns)

        grand_total = float(contingency.values.sum())
        row_totals = contingency.sum(axis=1)
        col_totals = contingency.sum(axis=0)

        chi2_stat = 0.0
        for r in rows:
            for c in cols:
                o = float(contingency.loc[r, c])
                e = float(row_totals[r]) * float(col_totals[c]) / grand_total
                if e > 0:
                    chi2_stat += (o - e) ** 2 / e

        df_val = (len(rows) - 1) * (len(cols) - 1)
        p_val = _p_from_chi2(chi2_stat, df_val)

        lines = [f"## 카이제곱 독립성 검정: {col_a} × {col_b}\n"]
        lines.append("### 교차표\n")
        header = f"| {col_a} \\ {col_b} | " + " | ".join([str(c) for c in cols]) + " | 합계 |"
        sep = "|------|" + "------|" * (len(cols) + 1)
        lines.append(header)
        lines.append(sep)
        for r in rows:
            vals = [str(int(contingency.loc[r, c])) for c in cols]
            lines.append(f"| {r} | " + " | ".join(vals) + f" | {int(row_totals[r])} |")
        col_tot_str = " | ".join([str(int(col_totals[c])) for c in cols])
        lines.append(f"| 합계 | {col_tot_str} | {int(grand_total)} |")

        lines.append("\n### 검정 결과\n")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 카이제곱 통계량 | {chi2_stat:.6f} |")
        lines.append(f"| 자유도 (df) | {df_val} |")
        lines.append(f"| p-value | {p_val:.6f} |")
        lines.append(f"\n**판정**: {_significance(p_val)}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 카이제곱 검정 실패: {e}"


def normality_test(conn_id: str, sql: str, col: str) -> str:
    """[Statistics] 정규성 검정 (Jarque-Bera).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        col: 검정할 수치형 컬럼명
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if col not in df.columns:
        return f"[ERROR] column '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        s = df[col].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            return f"[ERROR] '{col}'은 수치형 컬럼이 아닙니다."
        n = len(s)
        if n < 8:
            return f"[ERROR] Jarque-Bera 검정에는 최소 8개 데이터가 필요합니다. 현재: {n}개"

        skew = float(s.skew())
        kurt_excess = float(s.kurtosis())  # pandas kurtosis = excess kurtosis

        jb_stat = n / 6 * (skew ** 2 + kurt_excess ** 2 / 4)
        p_val = _p_from_chi2(jb_stat, df=2)

        lines = [f"## 정규성 검정 (Jarque-Bera): {col}\n"]
        lines.append(f"- **귀무가설 (H0)**: 데이터가 정규분포를 따름\n")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 표본 수 (n) | {n:,} |")
        lines.append(f"| 왜도 (Skewness) | {skew:.6f} |")
        lines.append(f"| 초과첨도 (Excess Kurtosis) | {kurt_excess:.6f} |")
        lines.append(f"| JB 통계량 | {jb_stat:.6f} |")
        lines.append(f"| 자유도 (df) | 2 |")
        lines.append(f"| p-value | {p_val:.6f} |")

        if p_val < 0.05:
            verdict = "정규분포를 따르지 않음 (p < 0.05)"
        else:
            verdict = "정규분포를 따른다고 볼 수 있음 (p ≥ 0.05)"
        lines.append(f"\n**판정**: {verdict}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 정규성 검정 실패: {e}"
