"""bi-agent 파일 데이터 소스 도구 — CSV, Excel 파일 로드 및 DuckDB SQL 쿼리."""
import os
import uuid
from pathlib import Path
from typing import Dict, Optional

from bi_agent_mcp.tools.db import _validate_select

_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
_files: Dict[str, dict] = {}  # file_id -> {path, df, name}


def _validate_path(path: str) -> Optional[str]:
    """파일 경로 검증. None=통과, str=오류 메시지."""
    abs_path = os.path.abspath(path)
    ext = Path(abs_path).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        return f"지원하지 않는 파일 형식: '{ext}'. CSV, XLSX, XLS만 허용됩니다."
    if not os.path.exists(abs_path):
        return f"파일을 찾을 수 없습니다: '{abs_path}'"
    return None


def connect_file(path: str, sheet: str = "") -> str:
    """[File] CSV 또는 Excel 파일을 로드하고 파일 ID를 반환합니다.

    Args:
        path: CSV(.csv) 또는 Excel(.xlsx/.xls) 파일 경로
        sheet: Excel 시트 이름 (비우면 첫 번째 시트 사용, CSV는 무시)
    """
    err = _validate_path(path)
    if err:
        return f"[ERROR] {err}"

    abs_path = os.path.abspath(path)
    ext = Path(abs_path).suffix.lower()

    try:
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(abs_path)
        else:
            df = pd.read_excel(abs_path, sheet_name=sheet if sheet else 0)
    except Exception as e:
        return f"[ERROR] 파일 로드 실패: {e}"

    file_id = f"file_{uuid.uuid4().hex[:8]}"
    _files[file_id] = {"path": abs_path, "df": df, "name": Path(abs_path).name}

    cols = ", ".join(df.columns.tolist()[:10])
    if len(df.columns) > 10:
        cols += f" ... (총 {len(df.columns)}개)"
    return (
        f"파일 로드 완료: {file_id}\n"
        f"  파일명: {Path(abs_path).name}\n"
        f"  행수: {len(df):,}\n"
        f"  컬럼 ({len(df.columns)}개): {cols}"
    )


def list_files() -> str:
    """[File] 로드된 파일 목록을 반환합니다."""
    if not _files:
        return "로드된 파일이 없습니다. connect_file을 먼저 호출하세요."
    lines = ["로드된 파일 목록:\n"]
    lines.append("| file_id | 파일명 | 행수 | 컬럼수 |")
    lines.append("| --- | --- | --- | --- |")
    for fid, info in _files.items():
        df = info["df"]
        lines.append(f"| {fid} | {info['name']} | {len(df):,} | {len(df.columns)} |")
    return "\n".join(lines)


def query_file(file_id: str, sql: str) -> str:
    """[File] 로드된 파일에 SQL 쿼리를 실행합니다. SELECT만 허용됩니다.

    Args:
        file_id: connect_file로 얻은 파일 ID
        sql: 실행할 SELECT SQL (테이블명으로 파일 이름 또는 'df' 사용)
    """
    if file_id not in _files:
        return f"[ERROR] 파일 ID '{file_id}'를 찾을 수 없습니다. list_files로 확인하세요."

    query = sql.strip()
    if "```" in query:
        lines_list = query.split("\n")
        query = "\n".join(l for l in lines_list if not l.startswith("```")).strip()

    err = _validate_select(query)
    if err:
        return f"[ERROR] {err}"

    df = _files[file_id]["df"]
    table_name = _files[file_id]["name"].replace(".", "_").replace("-", "_")

    try:
        import duckdb
        # DuckDB로 DataFrame에 SQL 실행
        # 테이블명을 df 또는 파일명으로 참조 가능하도록
        con = duckdb.connect()
        con.register("df", df)
        con.register(table_name, df)
        result = con.execute(query).fetchdf()
        con.close()
    except ImportError:
        try:
            import pandasql as ps
            env = {"df": df, table_name: df}
            result = ps.sqldf(query, env)
        except ImportError:
            return "[ERROR] duckdb 또는 pandasql이 필요합니다. pip install duckdb"
    except Exception as e:
        return f"[ERROR] 쿼리 실행 실패: {e}"

    if result.empty:
        return f"결과 없음 (SQL: `{query}`)"

    # 마크다운 테이블 생성
    cols = result.columns.tolist()
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows_md = []
    for _, row in result.iterrows():
        vals = [str(row[c]) for c in cols]
        rows_md.append("| " + " | ".join(vals) + " |")

    sql_preview = query[:80] + ("..." if len(query) > 80 else "")
    return (
        f"**{len(result)}건 반환** (SQL: `{sql_preview}`)\n\n"
        + header + "\n" + separator + "\n" + "\n".join(rows_md)
    )


def get_file_schema(file_id: str) -> str:
    """[File] 로드된 파일의 컬럼 정보를 반환합니다.

    Args:
        file_id: connect_file로 얻은 파일 ID
    """
    if file_id not in _files:
        return f"[ERROR] 파일 ID '{file_id}'를 찾을 수 없습니다."

    info = _files[file_id]
    df = info["df"]

    lines = [f"파일 '{info['name']}' 스키마 ({len(df):,}행)\n"]
    lines.append("| 컬럼명 | 타입 | NULL수 | 샘플값 |")
    lines.append("| --- | --- | --- | --- |")

    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isna().sum())
        sample = df[col].dropna().head(1)
        sample_val = str(sample.iloc[0]) if len(sample) > 0 else ""
        if len(sample_val) > 50:
            sample_val = sample_val[:47] + "..."
        lines.append(f"| {col} | {dtype} | {null_count} | {sample_val} |")

    return "\n".join(lines)
