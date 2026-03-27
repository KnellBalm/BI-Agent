"""A/B 테스트 전문 분석 도구 — 샘플 크기 계산, 다변형 비교, 세그먼트 분석, 시간적 효과."""
import itertools
import math
import logging
import pandas as pd
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

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


def _p_from_t(t_stat: float, df: int, two_tailed: bool = True) -> float:
    """t 통계량 → p값 계산."""
    if _HAS_SCIPY:
        p = float(_scipy_stats.t.sf(abs(t_stat), df))
        return p * 2 if two_tailed else p
    p = math.erfc(abs(t_stat) / math.sqrt(2))
    return p if two_tailed else p / 2


def _significance(p: float, alpha: float = 0.05) -> str:
    """p값 → 유의성 판정 문자열."""
    if p < 0.001:
        return "유의미한 차이 있음 (p < 0.001, ***)"
    elif p < 0.01:
        return f"유의미한 차이 있음 (p = {p:.4f}, **)"
    elif p < alpha:
        return f"유의미한 차이 있음 (p = {p:.4f}, *)"
    else:
        return f"유의미한 차이 없음 (p = {p:.4f})"


def ab_sample_size(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
    test_type: str = "proportion",
) -> str:
    """[ABTest] A/B 테스트 시작 전 필요한 그룹당 샘플 수를 계산합니다.

    Args:
        baseline_rate: 기준(A) 전환율 또는 평균. 예: 0.05 (5% 전환율), 100.0 (평균 구매액)
        mde: 최소 탐지 가능 효과 (상대적 변화율). 예: 0.20 = 20% 개선 탐지
        alpha: 1종 오류율(유의수준). 기본 0.05
        power: 검정력 (1 - 2종 오류율). 기본 0.80
        test_type: "proportion" (전환율) | "mean" (평균)
    """
    if baseline_rate <= 0:
        return "[ERROR] baseline_rate는 양수여야 합니다."
    if not (0 < mde < 1):
        return "[ERROR] mde는 0과 1 사이여야 합니다 (예: 0.20 = 20%)."
    if not (0 < alpha < 1):
        return "[ERROR] alpha는 0과 1 사이여야 합니다."
    if not (0 < power < 1):
        return "[ERROR] power는 0과 1 사이여야 합니다."
    if test_type not in ("proportion", "mean"):
        return "[ERROR] test_type은 'proportion' 또는 'mean'이어야 합니다."

    # z 값 계산
    if _HAS_SCIPY:
        z_alpha_2 = float(_scipy_stats.norm.ppf(1 - alpha / 2))
        z_beta = float(_scipy_stats.norm.ppf(power))
    else:
        _z_alpha_map = {0.05: 1.96, 0.01: 2.576, 0.10: 1.645}
        z_alpha_2 = _z_alpha_map.get(round(alpha, 4), 1.96)
        _z_power_map = {0.80: 0.842, 0.90: 1.282, 0.95: 1.645}
        z_beta = _z_power_map.get(round(power, 4), 0.842)

    delta = baseline_rate * mde

    if test_type == "proportion":
        p = baseline_rate
        n = ((z_alpha_2 + z_beta) ** 2 * 2 * p * (1 - p)) / (delta ** 2)
        target_rate = baseline_rate + delta
        type_label = "전환율"
        baseline_display = f"{baseline_rate * 100:.2f}%"
        target_display = f"{target_rate * 100:.2f}%"
    else:
        sigma = baseline_rate * 0.5
        n = ((z_alpha_2 + z_beta) ** 2 * 2 * sigma ** 2) / (delta ** 2)
        target_rate = baseline_rate + delta
        type_label = "평균"
        baseline_display = f"{baseline_rate:.4f}"
        target_display = f"{target_rate:.4f}"

    n_ceil = math.ceil(n)
    total = n_ceil * 2

    lines = [
        "## A/B 테스트 샘플 크기 계산",
        "",
        "### 입력 파라미터",
        "| 파라미터 | 값 |",
        "|---------|-----|",
        f"| 기준 {type_label} | {baseline_display} |",
        f"| 최소 탐지 가능 효과(MDE) | {mde * 100:.2f}% 개선 |",
        f"| 목표 {type_label} | {target_display} |",
        f"| 유의수준 (α) | {alpha} |",
        f"| 검정력 | {power * 100:.2f}% |",
        "",
        "### 결과",
        f"- **그룹당 필요 샘플 수**: {n_ceil:,}명",
        f"- **전체 필요 샘플 수**: {total:,}명 (A + B 합계)",
        "",
        "### 해석",
        f"- 각 그룹에 최소 {n_ceil:,}명이 필요합니다.",
    ]

    if test_type == "proportion":
        lines.append(
            f"- MDE {mde * 100:.0f}%는 {type_label}이 {baseline_display} → {target_display}로 개선될 때 탐지 가능합니다."
        )
    else:
        lines.append(
            f"- MDE {mde * 100:.0f}%는 {type_label}이 {baseline_display} → {target_display}로 변화할 때 탐지 가능합니다."
        )

    lines.append(f"- 실험 기간: 일 트래픽에 따라 계산 필요 (예: 일 500명 → 약 {n_ceil / 500:.1f}일)")

    return "\n".join(lines)


def ab_multivariate(
    conn_id: str,
    sql: str,
    group_col: str,
    metric_col: str,
    alpha: float = 0.05,
) -> str:
    """[ABTest] 3개 이상 변형(A/B/C/n)의 동시 비교 분석입니다.

    ANOVA F-검정으로 전체 유의성을 확인하고, Bonferroni 보정으로 쌍별 비교합니다.

    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: 변형 그룹 컬럼 (3개 이상 고유값)
        metric_col: 분석할 수치형 컬럼
        alpha: 유의수준 (기본 0.05)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    if group_col not in df.columns:
        return f"[ERROR] '{group_col}' 컬럼이 없습니다."
    if metric_col not in df.columns:
        return f"[ERROR] '{metric_col}' 컬럼이 없습니다."

    groups = df[group_col].unique()
    k = len(groups)

    if k < 3:
        return "[ERROR] ab_test_analysis를 사용하세요 (2그룹 비교)"

    group_data = [df[df[group_col] == g][metric_col].dropna().values for g in groups]

    # ANOVA
    if _HAS_SCIPY:
        f_stat, p_anova = _scipy_stats.f_oneway(*group_data)
        f_stat = float(f_stat)
        p_anova = float(p_anova)
    else:
        all_vals = np.concatenate(group_data)
        N = len(all_vals)
        grand_mean = all_vals.mean()
        ns = [len(g) for g in group_data]
        means = [g.mean() for g in group_data]

        between_var = sum(ns[i] * (means[i] - grand_mean) ** 2 for i in range(k)) / (k - 1)
        within_var = sum(np.sum((group_data[i] - means[i]) ** 2) for i in range(k)) / (N - k)
        f_stat = between_var / within_var if within_var > 0 else 0.0

        if _HAS_SCIPY:
            p_anova = float(_scipy_stats.f.sf(f_stat, k - 1, N - k))
        else:
            # 근사: F가 크면 p 작게
            p_anova = math.exp(-f_stat / 2) if f_stat > 0 else 1.0

    anova_sig = _significance(p_anova, alpha)

    # 기술통계
    desc_rows = []
    for g, gd in zip(groups, group_data):
        desc_rows.append({
            "그룹": str(g),
            "n": len(gd),
            "평균": gd.mean() if len(gd) > 0 else float("nan"),
            "표준편차": gd.std(ddof=1) if len(gd) > 1 else 0.0,
            "최솟값": gd.min() if len(gd) > 0 else float("nan"),
            "최댓값": gd.max() if len(gd) > 0 else float("nan"),
        })

    # 쌍별 비교 (Bonferroni)
    num_pairs = k * (k - 1) // 2
    alpha_adj = alpha / num_pairs

    pair_rows = []
    for (i, gi), (j, gj) in itertools.combinations(enumerate(groups), 2):
        gd_i = group_data[i]
        gd_j = group_data[j]
        mean_diff = gd_i.mean() - gd_j.mean()

        if _HAS_SCIPY:
            t_stat, p_pair = _scipy_stats.ttest_ind(gd_i, gd_j, equal_var=False)
            p_pair = float(p_pair)
        else:
            n_i, n_j = len(gd_i), len(gd_j)
            var_i = gd_i.var(ddof=1) if n_i > 1 else 0.0
            var_j = gd_j.var(ddof=1) if n_j > 1 else 0.0
            se = math.sqrt(var_i / n_i + var_j / n_j) if (var_i + var_j) > 0 else 1e-9
            t_stat = mean_diff / se
            dof = max(n_i + n_j - 2, 1)
            p_pair = _p_from_t(t_stat, dof)

        sig_label = "유의미함 (*)" if p_pair < alpha_adj else "유의미하지 않음"
        pair_rows.append({
            "비교": f"{gi} vs {gj}",
            "평균 차이": mean_diff,
            "p값": p_pair,
            "보정 후 유의성": sig_label,
        })

    # 출력 조립
    lines = [
        "## 다변형 A/B 테스트 분석",
        "",
        "### 그룹별 기술통계",
        "| 그룹 | n | 평균 | 표준편차 | 최솟값 | 최댓값 |",
        "|-----|---|-----|---------|------|------|",
    ]
    for r in desc_rows:
        lines.append(
            f"| {r['그룹']} | {r['n']} | {r['평균']:.4f} | {r['표준편차']:.4f} | {r['최솟값']:.4f} | {r['최댓값']:.4f} |"
        )

    lines += [
        "",
        "### ANOVA 결과",
        f"- F통계량: {f_stat:.4f}",
        f"- p값: {p_anova:.4f}",
        f"- 판정: {anova_sig}",
        "",
        f"### 쌍별 비교 (Bonferroni 보정, α_adj = {alpha_adj:.4f})",
        "| 비교 | 평균 차이 | p값 | 보정 후 유의성 |",
        "|-----|---------|-----|-------------|",
    ]
    for r in pair_rows:
        lines.append(
            f"| {r['비교']} | {r['평균 차이']:.4f} | {r['p값']:.4f} | {r['보정 후 유의성']} |"
        )

    return "\n".join(lines)


def ab_segment_breakdown(
    conn_id: str,
    sql: str,
    group_col: str,
    metric_col: str,
    segment_col: str,
    alpha: float = 0.05,
) -> str:
    """[ABTest] 세그먼트별 A/B 처리 효과를 분석하여 이질적 처리 효과(HTE)를 탐지합니다.

    전체 A/B 결과가 특정 세그먼트에서는 다르게 나타나는지 확인합니다.
    예: 신규/기존 사용자별, 기기별, 지역별 A/B 효과 차이.

    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: A/B 그룹 컬럼 (2개 고유값)
        metric_col: 분석할 수치형 컬럼
        segment_col: 세그먼트 컬럼 (예: device, region, user_type)
        alpha: 유의수준 (기본 0.05)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in (group_col, metric_col, segment_col):
        if col not in df.columns:
            return f"[ERROR] '{col}' 컬럼이 없습니다."

    groups = df[group_col].unique()
    if len(groups) != 2:
        return f"[ERROR] group_col은 정확히 2개의 고유값이 필요합니다. 현재: {len(groups)}개"

    g1_label, g2_label = groups[0], groups[1]

    def _run_ttest(data_g1, data_g2):
        n1, n2 = len(data_g1), len(data_g2)
        mean1, mean2 = data_g1.mean(), data_g2.mean()
        if _HAS_SCIPY:
            _, p = _scipy_stats.ttest_ind(data_g1, data_g2, equal_var=False)
            p = float(p)
        else:
            var1 = data_g1.var(ddof=1) if n1 > 1 else 0.0
            var2 = data_g2.var(ddof=1) if n2 > 1 else 0.0
            se = math.sqrt(var1 / n1 + var2 / n2) if (var1 + var2) > 0 else 1e-9
            t_stat = (mean1 - mean2) / se
            dof = max(n1 + n2 - 2, 1)
            p = _p_from_t(t_stat, dof)
        return mean1, mean2, n1, n2, p

    # 전체 결과
    g1_all = df[df[group_col] == g1_label][metric_col].dropna().values
    g2_all = df[df[group_col] == g2_label][metric_col].dropna().values
    mean1_all, mean2_all, n1_all, n2_all, p_all = _run_ttest(g1_all, g2_all)
    if mean1_all != 0:
        lift_all_str = f"{(mean2_all - mean1_all) / mean1_all * 100:+.1f}%"
    else:
        lift_all_str = "N/A"
    overall_sig = _significance(p_all, alpha)

    lines = [
        "## 세그먼트별 A/B 효과 분석",
        "",
        "### 전체 결과",
        f"- {g1_label} 그룹: n={n1_all}, 평균={mean1_all:.3f}",
        f"- {g2_label} 그룹: n={n2_all}, 평균={mean2_all:.3f}",
        f"- 전체 Lift: {lift_all_str}",
        f"- 전체 판정: {overall_sig}",
        "",
        "### 세그먼트별 결과",
        "| 세그먼트 | A 평균 | B 평균 | Lift | p값 | 유의성 |",
        "|---------|------|------|------|----|----|",
    ]

    segments = df[segment_col].unique()
    sig_count = 0
    sig_segments = []
    insig_segments = []

    for seg in segments:
        seg_df = df[df[segment_col] == seg]
        g1_seg = seg_df[seg_df[group_col] == g1_label][metric_col].dropna().values
        g2_seg = seg_df[seg_df[group_col] == g2_label][metric_col].dropna().values
        if len(g1_seg) < 2 or len(g2_seg) < 2:
            continue
        m1, m2, _, _, p_seg = _run_ttest(g1_seg, g2_seg)
        if m1 != 0:
            lift_seg_str = f"{(m2 - m1) / m1 * 100:+.1f}%"
        else:
            lift_seg_str = "N/A"
        is_sig = p_seg < alpha
        if is_sig:
            sig_label = "*"
            sig_count += 1
            sig_segments.append(str(seg))
        else:
            sig_label = "-"
            insig_segments.append(str(seg))
        lines.append(f"| {seg} | {m1:.3f} | {m2:.3f} | {lift_seg_str} | {p_seg:.4f} | {sig_label} |")

    total_segs = len(sig_segments) + len(insig_segments)
    lines += ["", "### 이질성 요약"]

    if total_segs == 0:
        lines.append("세그먼트별 분석에 충분한 데이터가 없습니다.")
    elif sig_count < total_segs * 0.5:
        sig_list = ", ".join(sig_segments) if sig_segments else "없음"
        insig_list = ", ".join(insig_segments) if insig_segments else "없음"
        lines.append(
            f"효과가 세그먼트에 따라 다릅니다. {sig_list}에서는 유의미하나 {insig_list}에서는 아닙니다."
        )
        lines.append("세그먼트별 맞춤 전략을 고려하세요.")
    else:
        lines.append("대부분의 세그먼트에서 일관된 효과가 확인됩니다.")

    return "\n".join(lines)


def ab_time_decay(
    conn_id: str,
    sql: str,
    group_col: str,
    metric_col: str,
    date_col: str,
    window_days: int = 7,
) -> str:
    """[ABTest] 실험 기간 동안 A/B 효과의 시간적 변화를 분석하고 novelty effect를 감지합니다.

    실험 초반 효과가 시간이 지나면서 줄어드는 경우(novelty effect)를 탐지합니다.
    각 기간 window별로 A/B 차이를 계산합니다.

    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: A/B 그룹 컬럼
        metric_col: 분석할 수치형 컬럼
        date_col: 날짜 컬럼
        window_days: 기간 창 크기 (기본 7일)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err

    for col in (group_col, metric_col, date_col):
        if col not in df.columns:
            return f"[ERROR] '{col}' 컬럼이 없습니다."

    groups = df[group_col].unique()
    if len(groups) != 2:
        return f"[ERROR] group_col은 정확히 2개의 고유값이 필요합니다. 현재: {len(groups)}개"

    g1_label, g2_label = groups[0], groups[1]

    try:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
    except Exception as e:
        return f"[ERROR] 날짜 변환 실패: {e}"

    min_date = df[date_col].min()
    df["_window_idx"] = ((df[date_col] - min_date).dt.days // window_days).astype(int)

    window_indices = sorted(df["_window_idx"].unique())
    if len(window_indices) < 2:
        return "[ERROR] 최소 2개 이상의 기간 창이 필요합니다."

    lines = [
        f"## A/B 효과 시간 변화 분석 (window={window_days}일)",
        "",
        "### 기간별 효과",
        "| 기간 | A 평균 | B 평균 | Lift | p값 | 유의성 |",
        "|-----|------|------|------|----|----|",
    ]

    lifts = []
    for idx in window_indices:
        w_df = df[df["_window_idx"] == idx]
        g1 = w_df[w_df[group_col] == g1_label][metric_col].dropna().values
        g2 = w_df[w_df[group_col] == g2_label][metric_col].dropna().values
        if len(g1) < 2 or len(g2) < 2:
            lifts.append(None)
            continue

        m1, m2 = g1.mean(), g2.mean()
        n1, n2 = len(g1), len(g2)

        if _HAS_SCIPY:
            _, p = _scipy_stats.ttest_ind(g1, g2, equal_var=False)
            p = float(p)
        else:
            var1 = g1.var(ddof=1) if n1 > 1 else 0.0
            var2 = g2.var(ddof=1) if n2 > 1 else 0.0
            se = math.sqrt(var1 / n1 + var2 / n2) if (var1 + var2) > 0 else 1e-9
            t_stat = (m1 - m2) / se
            dof = max(n1 + n2 - 2, 1)
            p = _p_from_t(t_stat, dof)

        if m1 != 0:
            lift = (m2 - m1) / m1 * 100
            lift_str = f"{lift:+.1f}%"
        else:
            lift = None
            lift_str = "N/A"

        if p < 0.001:
            sig_label = "***"
        elif p < 0.01:
            sig_label = "**"
        elif p < 0.05:
            sig_label = "*"
        else:
            sig_label = "-"

        period_label = f"{idx + 1}주차" if window_days == 7 else f"기간 {idx + 1}"
        lines.append(f"| {period_label} | {m1:.3f} | {m2:.3f} | {lift_str} | {p:.4f} | {sig_label} |")
        lifts.append(lift)

    valid_lifts = [lft for lft in lifts if lft is not None]
    lines += ["", "### Novelty Effect 판정"]

    if len(valid_lifts) < 2:
        lines.append("충분한 기간 데이터가 없어 Novelty Effect를 판정할 수 없습니다.")
        return "\n".join(lines)

    if len(valid_lifts) >= 4:
        early_avg = sum(valid_lifts[:2]) / 2
        late_avg = sum(valid_lifts[-2:]) / 2
    else:
        early_avg = valid_lifts[0]
        late_avg = valid_lifts[-1]

    if early_avg > late_avg * 1.5 and early_avg > 0:
        lines.append(
            f"**Novelty Effect 감지**: 초기 효과({early_avg:.1f}%)가 후반({late_avg:.1f}%)에 비해 현저히 큽니다."
        )
        lines.append("실험 결과를 신중하게 해석하세요. 충분한 실험 기간(최소 2-4주) 후 재평가를 권장합니다.")
    else:
        lines.append(
            f"Novelty Effect 없음: 효과가 기간에 걸쳐 안정적입니다. (초기: {early_avg:.1f}%, 후반: {late_avg:.1f}%)"
        )

    return "\n".join(lines)
