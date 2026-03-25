"""bi-agent compare 도구 — 두 쿼리 결과를 비교하여 추가/삭제/변경된 행을 분석합니다."""
from typing import List, Optional

from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select


def compare_queries(
    conn_id: str,
    sql_a: str,
    sql_b: str,
    key_columns: Optional[List[str]] = None,
) -> str:
    """두 쿼리 결과를 비교하여 추가/삭제/변경된 행을 분석합니다.

    Args:
        conn_id: 연결 ID
        sql_a: 기준 쿼리 (이전/A)
        sql_b: 비교 쿼리 (이후/B)
        key_columns: 행을 식별하는 키 컬럼 목록 (없으면 인덱스 기반 비교)
    """
    try:
        import pandas as pd
    except ImportError:
        return "[ERROR] pandas가 설치되어 있지 않습니다."

    # conn_id 검증
    if conn_id not in _connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    info = _connections[conn_id]

    # 쿼리 검증
    err_a = _validate_select(sql_a)
    if err_a:
        return f"[ERROR] sql_a: {err_a}"

    err_b = _validate_select(sql_b)
    if err_b:
        return f"[ERROR] sql_b: {err_b}"

    # 두 쿼리 실행
    try:
        conn_a = _get_conn(info)
        conn_b = _get_conn(info)
    except Exception as e:
        return f"[ERROR] DB 연결 실패: {e}"

    try:
        df_a = _execute_to_df(conn_a, info.db_type, sql_a, pd)
    except Exception as e:
        return f"[ERROR] sql_a 실행 실패: {e}"
    finally:
        try:
            conn_a.close()
        except Exception:
            pass

    try:
        df_b = _execute_to_df(conn_b, info.db_type, sql_b, pd)
    except Exception as e:
        return f"[ERROR] sql_b 실행 실패: {e}"
    finally:
        try:
            conn_b.close()
        except Exception:
            pass

    if df_a.empty and df_b.empty:
        return "두 쿼리 모두 결과 없음"

    if key_columns:
        return _compare_by_keys(df_a, df_b, key_columns, pd)
    else:
        return _compare_by_index(df_a, df_b, pd)


def _execute_to_df(conn, db_type: str, sql: str, pd):
    """쿼리를 실행하여 DataFrame으로 반환합니다."""
    if db_type == "postgresql":
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return pd.DataFrame(columns=columns)
        return pd.DataFrame([dict(r) for r in rows])
    else:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(rows, columns=columns)


def _compare_by_keys(df_a, df_b, key_columns: list, pd) -> str:
    """key_columns 기반 outer join으로 추가/삭제/변경 분류."""
    # key_columns 존재 여부 검증
    for col in key_columns:
        if col not in df_a.columns and col not in df_b.columns:
            return f"[ERROR] 키 컬럼 '{col}'이 두 쿼리 결과에 모두 없습니다."

    merged = pd.merge(df_a, df_b, on=key_columns, how="outer", suffixes=("_a", "_b"), indicator=True)

    added = merged[merged["_merge"] == "right_only"].drop(columns=["_merge"])
    deleted = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
    both = merged[merged["_merge"] == "both"].drop(columns=["_merge"])

    # 변경된 행 탐지: _a/_b 접미사 컬럼 비교
    changed_mask = pd.Series([False] * len(both), index=both.index)
    value_cols_a = [c for c in both.columns if c.endswith("_a")]
    for col_a in value_cols_a:
        col_b = col_a[:-2] + "_b"
        if col_b in both.columns:
            changed_mask = changed_mask | (both[col_a].astype(str) != both[col_b].astype(str))

    changed = both[changed_mask]
    unchanged = both[~changed_mask]

    lines = ["## 쿼리 비교 결과 (key 기반)\n"]
    lines.append(f"- A 행 수: {len(df_a)}, B 행 수: {len(df_b)}")
    lines.append(f"- 추가된 행: {len(added)}")
    lines.append(f"- 삭제된 행: {len(deleted)}")
    lines.append(f"- 변경된 행: {len(changed)}")
    lines.append(f"- 동일한 행: {len(unchanged)}\n")

    if not added.empty:
        lines.append("### 추가된 행 (최대 5행)")
        lines.append(added.head(5).to_markdown(index=False))
        lines.append("")

    if not deleted.empty:
        lines.append("### 삭제된 행 (최대 5행)")
        lines.append(deleted.head(5).to_markdown(index=False))
        lines.append("")

    if not changed.empty:
        lines.append("### 변경된 행 (최대 5행)")
        lines.append(changed.head(5).to_markdown(index=False))
        lines.append("")

    # 수치 컬럼 변화량/변화율
    numeric_summary = _numeric_diff_summary(both, value_cols_a, pd)
    if numeric_summary:
        lines.append("### 수치 컬럼 변화 요약")
        lines.append(numeric_summary)

    return "\n".join(lines)


def _compare_by_index(df_a, df_b, pd) -> str:
    """인덱스 기반 비교."""
    len_a, len_b = len(df_a), len(df_b)
    min_len = min(len_a, len_b)

    added_count = max(0, len_b - len_a)
    deleted_count = max(0, len_a - len_b)

    lines = ["## 쿼리 비교 결과 (인덱스 기반)\n"]
    lines.append(f"- A 행 수: {len_a}, B 행 수: {len_b}")
    lines.append(f"- 추가된 행: {added_count}")
    lines.append(f"- 삭제된 행: {deleted_count}\n")

    if added_count > 0:
        lines.append("### 추가된 행 (최대 5행)")
        lines.append(df_b.iloc[len_a:].head(5).to_markdown(index=False))
        lines.append("")

    if deleted_count > 0:
        lines.append("### 삭제된 행 (최대 5행)")
        lines.append(df_a.iloc[len_b:].head(5).to_markdown(index=False))
        lines.append("")

    # 공통 구간에서 변경된 행 찾기
    if min_len > 0:
        sub_a = df_a.iloc[:min_len].reset_index(drop=True)
        sub_b = df_b.iloc[:min_len].reset_index(drop=True)

        # 공통 컬럼만 비교
        common_cols = [c for c in sub_a.columns if c in sub_b.columns]
        if common_cols:
            diff_mask = (sub_a[common_cols].astype(str) != sub_b[common_cols].astype(str)).any(axis=1)
            changed_indices = diff_mask[diff_mask].index.tolist()

            lines.append(f"- 값이 다른 행 (공통 구간): {len(changed_indices)}\n")
            if changed_indices:
                lines.append("### 변경된 행 샘플 (A 기준, 최대 5행)")
                lines.append(sub_a.loc[changed_indices[:5]].to_markdown(index=True))
                lines.append("")
                lines.append("### 변경된 행 샘플 (B 기준, 최대 5행)")
                lines.append(sub_b.loc[changed_indices[:5]].to_markdown(index=True))
                lines.append("")

            # 수치 컬럼 변화량/변화율
            numeric_cols = [c for c in common_cols if pd.api.types.is_numeric_dtype(sub_a[c])]
            if numeric_cols:
                lines.append("### 수치 컬럼 변화 요약")
                for col in numeric_cols:
                    try:
                        sum_a = sub_a[col].sum()
                        sum_b = sub_b[col].sum()
                        delta = sum_b - sum_a
                        rate = (delta / sum_a * 100) if sum_a != 0 else float("inf")
                        lines.append(f"- {col}: 합계 {sum_a:.4g} → {sum_b:.4g} (변화량: {delta:+.4g}, 변화율: {rate:+.2f}%)")
                    except Exception:
                        pass

    return "\n".join(lines)


def _numeric_diff_summary(both_df, value_cols_a: list, pd) -> str:
    """수치 컬럼의 변화량/변화율 요약."""
    lines = []
    for col_a in value_cols_a:
        col_b = col_a[:-2] + "_b"
        if col_b not in both_df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(both_df[col_a]):
            continue
        try:
            sum_a = both_df[col_a].sum()
            sum_b = both_df[col_b].sum()
            delta = sum_b - sum_a
            rate = (delta / sum_a * 100) if sum_a != 0 else float("inf")
            col_name = col_a[:-2]
            lines.append(f"- {col_name}: 합계 {sum_a:.4g} → {sum_b:.4g} (변화량: {delta:+.4g}, 변화율: {rate:+.2f}%)")
        except Exception:
            pass
    return "\n".join(lines)
