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


_QUERY_HISTORY_FILE = Path("~/.config/bi-agent/query_history.json").expanduser()


def load_domain_context(sections: str = "all") -> str:
    """비즈니스 도메인 컨텍스트를 로드합니다. context/ 디렉토리의 마크다운 파일을 읽어 분석에 활용할 수 있습니다.

    Args:
        sections: 로드할 섹션. "all"(전체), "business"(비즈니스 개요),
                  "data_sources"(데이터 소스), "kpis"(KPI 정의),
                  "patterns"(분석 패턴), "glossary"(용어사전)
    """
    _SECTION_MAP = {
        "business": "01_business_context.md",
        "data_sources": "02_data_sources.md",
        "kpis": "03_kpi_dictionary.md",
        "patterns": "04_analysis_patterns.md",
        "glossary": "05_glossary.md",
    }

    context_dir = Path.cwd() / "context"
    if not context_dir.exists():
        return (
            "[INFO] context/ 디렉토리가 없습니다.\n"
            "비즈니스 도메인 지식을 추가하면 분석 품질이 향상됩니다.\n"
            "context/ 디렉토리를 생성하고 템플릿 파일을 작성하세요."
        )

    if sections == "all":
        targets = list(_SECTION_MAP.values())
    else:
        requested = [s.strip() for s in sections.split(",")]
        targets = [_SECTION_MAP[s] for s in requested if s in _SECTION_MAP]
        if not targets:
            return f"[ERROR] 알 수 없는 섹션: {sections}. 사용 가능: all, {', '.join(_SECTION_MAP.keys())}"

    parts = []
    for filename in targets:
        filepath = context_dir / filename
        if filepath.exists():
            try:
                content = filepath.read_text(encoding="utf-8")
                parts.append(f"### [{filename}]\n{content}")
            except OSError:
                pass

    if not parts:
        return "[INFO] context/ 파일이 없거나 읽을 수 없습니다. 도메인 지식 파일을 작성하세요."

    return "## 비즈니스 도메인 컨텍스트\n\n" + "\n\n---\n\n".join(parts)


def list_query_history(limit: int = 20) -> str:
    """최근 실행한 쿼리 이력을 조회합니다.

    Args:
        limit: 반환할 최근 쿼리 수 (기본 20, 최대 100)
    """
    limit = min(max(1, limit), 100)

    if not _QUERY_HISTORY_FILE.exists():
        return "쿼리 이력이 없습니다. run_query를 사용하면 자동으로 기록됩니다."

    try:
        with _QUERY_HISTORY_FILE.open("r", encoding="utf-8") as f:
            history = json.load(f)
    except (json.JSONDecodeError, OSError):
        return "[ERROR] 쿼리 이력 파일을 읽을 수 없습니다."

    if not history:
        return "쿼리 이력이 없습니다."

    recent = history[-limit:][::-1]  # 최신 순

    lines = [f"최근 {len(recent)}개 쿼리 이력:\n"]
    lines.append("| # | 시각 | 연결 ID | 행수 | SQL 미리보기 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, entry in enumerate(recent, 1):
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        conn_id = entry.get("conn_id", "")
        row_count = entry.get("row_count", 0)
        sql = entry.get("sql", "")
        sql_preview = sql[:60].replace("\n", " ").strip() + ("..." if len(sql) > 60 else "")
        lines.append(f"| {i} | {ts} | {conn_id} | {row_count} | `{sql_preview}` |")
    return "\n".join(lines)


def suggest_analysis(data_context: str, question: str = "") -> str:
    """
    제공된 스키마/데이터 컨텍스트와 사용자의 질문을 바탕으로 분석 방향을 제안합니다.

    Args:
        data_context: 테이블 스키마나 샘플 데이터의 간략한 정보
        question: 사용자가 해결하고자 하는 비즈니스 질문

    Returns:
        분석 방향을 담은 구조화된 가이드 문자열
    """
    # 도메인 컨텍스트 로드 시도
    domain_context = ""
    context_dir = Path.cwd() / "context"
    if context_dir.exists():
        for fname in ["03_kpi_dictionary.md", "04_analysis_patterns.md"]:
            fpath = context_dir / fname
            if fpath.exists():
                try:
                    domain_context += fpath.read_text(encoding="utf-8")[:2000] + "\n\n"
                except OSError:
                    pass

    question_line = f"다음은 '{question}'에 대한 분석을 돕기 위해 제안하는 표준 접근법입니다.\n\n" if question else "다음은 분석을 돕기 위해 제안하는 표준 접근법입니다.\n\n"

    result = (
        question_line
        + "1. **핵심 지표 정의**: 비즈니스 질문에 직결되는 주요 지표(KPI)를 정의하세요.\n"
        "2. **데이터 필터링/그루핑 기준**: 기준 날짜, 특정 조건(예: 지역, 카테고리) 및 차원(Dimension)을 설정하세요.\n"
        "3. **비교 분석 요소**: 전월/전년 대비 비교, 시계열 추이 분석, 집단 간 비교 중 적절한 방식을 제안하세요.\n"
        "4. **추천 다음 단계 (SQL 초안)**: 위 내용을 구현하기 위한 구체적인 SQL 쿼리문 초안을 생성하세요.\n\n"
        f"**현재 데이터 컨텍스트 요약**:\n{data_context}\n\n"
        "이 지침에 따라 구체적인 분석 방향과 첫 번째 쿼리를 생성하여 사용자에게 제시해 주십시오."
    )

    if domain_context:
        result += f"\n\n## 도메인 컨텍스트 기반 제안:\n{domain_context}"

    return result
