"""프로덕트 분석 도구 — active_users, retention_curve, feature_adoption, ab_test_analysis, user_journey."""
import logging
import math
import numpy as np
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


def active_users(conn_id: str, sql: str, user_col: str, date_col: str, period: str = "day") -> str:
    """[Product] 기간별 활성 사용자 수(DAU/WAU/MAU) 집계.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        user_col: 사용자 식별 컬럼
        date_col: 날짜 컬럼
        period: "day"→DAU, "week"→WAU, "month"→MAU
    """
    period_map = {"day": ("D", "DAU"), "week": ("W", "WAU"), "month": ("ME", "MAU")}
    if period not in period_map:
        return f"[ERROR] period '{period}'은 지원하지 않습니다. 사용 가능: {list(period_map.keys())}"

    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if user_col not in df.columns:
        return f"[ERROR] user_col '{user_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if date_col not in df.columns:
        return f"[ERROR] date_col '{date_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[date_col] = pd.to_datetime(df[date_col])
        freq, label = period_map[period]
        agg = df.set_index(date_col).resample(freq)[user_col].nunique()
        agg = agg[agg > 0]

        lines = [f"## 활성 사용자 분석 ({label})\n"]
        lines.append(f"| 기간 | 활성 사용자 수 |")
        lines.append("|------|---------------|")
        for idx, val in agg.items():
            lines.append(f"| {str(idx)[:10]} | {val:,} |")

        if len(agg) > 0:
            avg_val = agg.mean()
            max_val = agg.max()
            min_val = agg.min()
            lines.append(f"\n### 요약")
            lines.append(f"- 평균 {label}: **{avg_val:,.1f}명**")
            lines.append(f"- 최대 {label}: **{max_val:,}명**")
            lines.append(f"- 최소 {label}: **{min_val:,}명**")
            lines.append(f"- 분석 기간: {len(agg)}개 {period}")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 활성 사용자 분석 실패: {e}"


def retention_curve(conn_id: str, sql: str, user_col: str, date_col: str, cohort_col: Optional[str] = None) -> str:
    """[Product] 코호트별 주차 리텐션 곡선 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        user_col: 사용자 식별 컬럼
        date_col: 활동 날짜 컬럼
        cohort_col: 코호트 기준 컬럼 (None이면 date_col의 첫 방문일로 자동 생성)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if user_col not in df.columns:
        return f"[ERROR] user_col '{user_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if date_col not in df.columns:
        return f"[ERROR] date_col '{date_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if cohort_col and cohort_col not in df.columns:
        return f"[ERROR] cohort_col '{cohort_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[date_col] = pd.to_datetime(df[date_col])

        if cohort_col:
            df["_cohort_date"] = pd.to_datetime(df[cohort_col])
        else:
            first_visit = df.groupby(user_col)[date_col].min().rename("_cohort_date")
            df = df.merge(first_visit, on=user_col)

        df["_cohort_week"] = df["_cohort_date"].dt.to_period("W")
        df["_activity_week"] = df[date_col].dt.to_period("W")

        def week_diff(row):
            try:
                return (row["_activity_week"] - row["_cohort_week"]).n
            except Exception:
                return 0

        df["_week_num"] = df.apply(week_diff, axis=1)
        df = df[df["_week_num"] >= 0]

        MAX_WEEKS = 12
        df = df[df["_week_num"] <= MAX_WEEKS]

        cohort_sizes = df[df["_week_num"] == 0].groupby("_cohort_week")[user_col].nunique()
        retention = df.groupby(["_cohort_week", "_week_num"])[user_col].nunique().unstack(fill_value=0)

        weeks = sorted([w for w in retention.columns if w <= MAX_WEEKS])

        lines = ["## 리텐션 곡선 (코호트 × 주차)\n"]
        week_headers = " | ".join([f"W+{w}" for w in weeks])
        lines.append(f"| 코호트 | 코호트 크기 | {week_headers} |")
        lines.append("|--------|------------|" + "---------|" * len(weeks))

        for cohort, size in cohort_sizes.items():
            row_vals = []
            for w in weeks:
                if w in retention.columns and cohort in retention.index:
                    cnt = retention.loc[cohort, w]
                    pct = cnt / size * 100 if size > 0 else 0
                    row_vals.append(f"{pct:.0f}%")
                else:
                    row_vals.append("—")
            lines.append(f"| {cohort} | {size:,} | " + " | ".join(row_vals) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 리텐션 분석 실패: {e}"


def feature_adoption(conn_id: str, sql: str, user_col: str, feature_col: str, date_col: Optional[str] = None) -> str:
    """[Product] 기능별 도입률 분석.
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        user_col: 사용자 식별 컬럼
        feature_col: 기능명 컬럼
        date_col: 날짜 컬럼 (있으면 기간별 트렌드 포함)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if user_col not in df.columns:
        return f"[ERROR] user_col '{user_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if feature_col not in df.columns:
        return f"[ERROR] feature_col '{feature_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if date_col and date_col not in df.columns:
        return f"[ERROR] date_col '{date_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        total_users = df[user_col].nunique()
        if total_users == 0:
            return "[ERROR] 데이터에 사용자가 없습니다."

        feature_users = df.groupby(feature_col)[user_col].nunique().reset_index()
        feature_users.columns = [feature_col, "사용자_수"]
        feature_users["도입률(%)"] = (feature_users["사용자_수"] / total_users * 100).round(1)
        feature_users = feature_users.sort_values("도입률(%)", ascending=False)

        lines = [f"## 기능 도입률 분석 (전체 사용자: {total_users:,}명)\n"]
        lines.append(f"| 기능 | 사용자 수 | 도입률(%) |")
        lines.append("|------|----------|----------|")
        for _, row in feature_users.iterrows():
            lines.append(f"| {row[feature_col]} | {row['사용자_수']:,} | {row['도입률(%)']:.1f}% |")

        top = feature_users.iloc[0]
        bottom = feature_users.iloc[-1]
        lines.append(f"\n### 요약")
        lines.append(f"- 최고 도입 기능: **{top[feature_col]}** ({top['도입률(%)']:.1f}%)")
        lines.append(f"- 최저 도입 기능: **{bottom[feature_col]}** ({bottom['도입률(%)']:.1f}%)")

        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df["_month"] = df[date_col].dt.to_period("M")
            trend = df.groupby(["_month", feature_col])[user_col].nunique().unstack(fill_value=0)
            features = list(feature_users[feature_col])
            trend_features = [f for f in features if f in trend.columns][:5]

            if trend_features:
                lines.append(f"\n### 월별 기능 사용 트렌드 (상위 {len(trend_features)}개)\n")
                header = "| 기간 | " + " | ".join([str(f) for f in trend_features]) + " |"
                lines.append(header)
                lines.append("|------|" + "------|" * len(trend_features))
                for idx, row in trend.iterrows():
                    vals = [str(int(row[f])) if f in row.index else "0" for f in trend_features]
                    lines.append(f"| {idx} | " + " | ".join(vals) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 기능 도입률 분석 실패: {e}"


def ab_test_analysis(conn_id: str, sql: str, group_col: str, metric_col: str, confidence: float = 0.95) -> str:
    """[Product] A/B 테스트 통계 분석 (scipy 미사용, numpy + math만으로 구현).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        group_col: 그룹 구분 컬럼 (정확히 2개 고유값)
        metric_col: 분석할 수치형 컬럼
        confidence: 신뢰 수준 (기본 0.95)
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    if group_col not in df.columns:
        return f"[ERROR] group_col '{group_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"
    if metric_col not in df.columns:
        return f"[ERROR] metric_col '{metric_col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        groups = df[group_col].unique()
        if len(groups) != 2:
            return f"[ERROR] group_col '{group_col}'은 정확히 2개의 고유값이 필요합니다. 현재: {list(groups)}"

        g1_name, g2_name = groups[0], groups[1]
        g1 = df[df[group_col] == g1_name][metric_col].dropna().values.astype(float)
        g2 = df[df[group_col] == g2_name][metric_col].dropna().values.astype(float)

        if len(g1) < 2 or len(g2) < 2:
            return "[ERROR] 각 그룹에 최소 2개 이상의 데이터가 필요합니다."

        n1, n2 = len(g1), len(g2)
        mean1, mean2 = np.mean(g1), np.mean(g2)
        std1, std2 = np.std(g1, ddof=1), np.std(g2, ddof=1)

        # Welch's z-test (정규분포 근사)
        se = math.sqrt(std1 ** 2 / n1 + std2 ** 2 / n2)
        if se == 0:
            z_stat = 0.0
            p_value = 1.0
        else:
            z_stat = (mean1 - mean2) / se
            # p-value: 양측 검정, 정규분포 근사 (math.erfc 사용)
            p_value = math.erfc(abs(z_stat) / math.sqrt(2))

        alpha = 1.0 - confidence
        significant = p_value < alpha
        verdict = "유의미한 차이 있음" if significant else "유의미한 차이 없음"

        lift = (mean1 - mean2) / abs(mean2) * 100 if mean2 != 0 else float("nan")

        lines = [f"## A/B 테스트 분석 (신뢰 수준: {confidence*100:.0f}%)\n"]
        lines.append("| 지표 | " + str(g1_name) + " | " + str(g2_name) + " |")
        lines.append("|------|------|------|")
        lines.append(f"| 샘플 수 | {n1:,} | {n2:,} |")
        lines.append(f"| 평균 | {mean1:.4f} | {mean2:.4f} |")
        lines.append(f"| 표준편차 | {std1:.4f} | {std2:.4f} |")
        lines.append(f"\n### 통계 검정 결과")
        lines.append(f"- **Z-통계량**: {z_stat:.4f}")
        lines.append(f"- **p-value**: {p_value:.4f}")
        lines.append(f"- **알파(α)**: {alpha:.2f}")
        if not math.isnan(lift):
            lines.append(f"- **상대적 변화(Lift)**: {lift:+.2f}%")
        lines.append(f"\n**판정: {verdict}**")
        if significant:
            better = str(g1_name) if mean1 > mean2 else str(g2_name)
            lines.append(f"→ **{better}** 그룹이 통계적으로 유의미하게 높은 성과를 보입니다.")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] A/B 테스트 분석 실패: {e}"


def user_journey(conn_id: str, sql: str, user_col: str, event_col: str, time_col: str, max_steps: int = 5) -> str:
    """[Product] 사용자 이벤트 시퀀스 분석 (Top-N 패턴 + 마르코프 전환 매트릭스).
    Args:
        conn_id: DB 연결 ID
        sql: 데이터 조회 SQL
        user_col: 사용자 식별 컬럼
        event_col: 이벤트명 컬럼
        time_col: 이벤트 시간 컬럼
        max_steps: 상위 시퀀스 패턴 수
    """
    df, err = _fetch_df(conn_id, sql)
    if err:
        return err
    for col in [user_col, event_col, time_col]:
        if col not in df.columns:
            return f"[ERROR] 컬럼 '{col}'이 데이터에 없습니다. 사용 가능: {list(df.columns)}"

    try:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values([user_col, time_col])

        # 사용자별 이벤트 시퀀스 생성
        sequences = df.groupby(user_col)[event_col].apply(list)

        # Top-N 시퀀스 패턴
        from collections import Counter
        seq_counter = Counter()
        for seq in sequences:
            # 연속 최대 max_steps 이벤트 슬라이딩 윈도우
            for i in range(len(seq) - 1):
                end = min(i + max_steps, len(seq))
                pattern = " → ".join(seq[i:end])
                seq_counter[pattern] += 1

        lines = [f"## 사용자 여정 분석\n"]
        lines.append(f"### Top {max_steps} 시퀀스 패턴\n")
        lines.append("| 순위 | 시퀀스 패턴 | 빈도 |")
        lines.append("|------|------------|------|")
        for rank, (pattern, cnt) in enumerate(seq_counter.most_common(max_steps), 1):
            lines.append(f"| {rank} | {pattern} | {cnt:,} |")

        # 마르코프 1차 전환 매트릭스
        events = sorted(df[event_col].unique())
        transition = pd.DataFrame(0, index=events, columns=events)
        for seq in sequences:
            for i in range(len(seq) - 1):
                from_event = seq[i]
                to_event = seq[i + 1]
                if from_event in transition.index and to_event in transition.columns:
                    transition.loc[from_event, to_event] += 1

        # 전환율로 정규화
        row_sums = transition.sum(axis=1)
        transition_pct = transition.div(row_sums, axis=0).fillna(0) * 100

        lines.append(f"\n### 이벤트 전환 매트릭스 (%)\n")
        header = "| 이벤트(From\\To) | " + " | ".join(events) + " |"
        lines.append(header)
        lines.append("|----------------|" + "------|" * len(events))
        for from_event in events:
            vals = [f"{transition_pct.loc[from_event, to]:.1f}%" for to in events]
            lines.append(f"| {from_event} | " + " | ".join(vals) + " |")

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 사용자 여정 분석 실패: {e}"
