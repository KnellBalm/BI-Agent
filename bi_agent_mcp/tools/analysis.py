"""
데이터 분석 제안, 쿼리 내역 저장, 마크다운 리포트 생성 도구.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 저장 공간 설정
CONFIG_DIR = Path.home() / ".bi-agent-mcp"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
QUERIES_FILE = CONFIG_DIR / "saved_queries.json"


def generate_report(sections: list) -> str:
    """
    sections 목록으로 마크다운 BI 리포트 파일을 생성합니다.

    Args:
        sections: [{"title": str, "content": str}, ...] 형식의 섹션 목록

    Returns:
        생성된 파일의 절대 경로 (문자열)
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

    download_dir = Path.home().expanduser() / "Downloads"
    if not download_dir.exists():
        download_dir = Path.home().expanduser()

    file_path = download_dir / f"{timestamp}_bi_report.md"

    lines = [f"# BI 리포트", f"생성 시각: {datetime_str}", ""]

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        lines.append(f"## {title}")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    full_content = "\n".join(lines)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        return str(file_path)
    except Exception as e:
        logger.error(f"리포트 생성 오류: {e}")
        return f"[ERROR] 리포트 파일 생성 실패: {e}"


def save_query(name: str, sql: str, connection_id: str = "") -> str:
    """
    나중에 재사용할 수 있도록 SQL 쿼리를 JSON 파일에 저장합니다.

    Args:
        name: 쿼리 이름 (예: "월별 매출 추이")
        sql: 저장할 SQL 쿼리 문자열
        connection_id: 쿼리가 실행되어야 할 DB 연결 ID (기본값: "")

    Returns:
        저장 결과 메시지
    """
    queries = {}
    if QUERIES_FILE.exists():
        try:
            with open(QUERIES_FILE, "r", encoding="utf-8") as f:
                queries = json.load(f)
        except Exception as e:
            logger.warning(f"기존 쿼리 파일을 읽는 중 오류 발생: {e}")

    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    queries[name] = {
        "sql": sql,
        "connection_id": connection_id,
        "saved_at": saved_at,
    }

    try:
        with open(QUERIES_FILE, "w", encoding="utf-8") as f:
            json.dump(queries, f, ensure_ascii=False, indent=2)
        return f"[SUCCESS] 쿼리 '{name}' 저장 완료 (경로: {QUERIES_FILE})"
    except Exception as e:
        logger.error(f"쿼리 저장 중 오류 발생: {e}")
        return f"[ERROR] 쿼리 저장에 실패했습니다: {e}"


def list_saved_queries() -> str:
    """
    현재까지 저장된 쿼리 목록을 마크다운 테이블 형식으로 반환합니다.
    """
    if not QUERIES_FILE.exists():
        return "저장된 쿼리가 없습니다."

    try:
        with open(QUERIES_FILE, "r", encoding="utf-8") as f:
            queries = json.load(f)

        if not queries:
            return "저장된 쿼리가 없습니다."

        header = "| 이름 | 연결 ID | SQL 미리보기 (50자) | 저장 시각 |"
        separator = "|------|---------|---------------------|-----------|"
        rows = [header, separator]

        for name, info in queries.items():
            connection_id = info.get("connection_id", "")
            sql_preview = info.get("sql", "")[:50].replace("\n", " ")
            saved_at = info.get("saved_at", "")
            rows.append(f"| {name} | {connection_id} | {sql_preview} | {saved_at} |")

        return "\n".join(rows)
    except Exception as e:
        logger.error(f"쿼리 목록 조회 중 오류 발생: {e}")
        return f"[ERROR] 쿼리 목록을 불러오지 못했습니다: {e}"


def suggest_analysis(data_context: str, question: str) -> str:
    """
    제공된 스키마/데이터 컨텍스트와 사용자의 질문을 바탕으로 분석 방향을 제안합니다.

    Args:
        data_context: 테이블 스키마나 샘플 데이터의 간략한 정보
        question: 사용자가 해결하고자 하는 비즈니스 질문

    Returns:
        분석 방향을 담은 구조화된 가이드 문자열
    """
    return (
        f"다음은 '{question}'에 대한 분석을 돕기 위해 제안하는 표준 접근법입니다.\n\n"
        "1. **핵심 지표 정의**: 비즈니스 질문에 직결되는 주요 지표(KPI)를 정의하세요.\n"
        "2. **데이터 필터링/그루핑 기준**: 기준 날짜, 특정 조건(예: 지역, 카테고리) 및 차원(Dimension)을 설정하세요.\n"
        "3. **비교 분석 요소**: 전월/전년 대비 비교, 시계열 추이 분석, 집단 간 비교 중 적절한 방식을 제안하세요.\n"
        "4. **추천 다음 단계 (SQL 초안)**: 위 내용을 구현하기 위한 구체적인 SQL 쿼리문 초안을 생성하세요.\n\n"
        f"**현재 데이터 컨텍스트 요약**:\n{data_context}\n\n"
        "이 지침에 따라 구체적인 분석 방향과 첫 번째 쿼리를 생성하여 사용자에게 제시해 주십시오."
    )
