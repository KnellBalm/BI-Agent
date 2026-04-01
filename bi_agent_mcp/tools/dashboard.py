"""bi-agent 대시보드 도구 — Chart.js 기반 HTML 인터랙티브 대시보드 생성."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


_CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"

_DASHBOARD_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; }
header { background: #1a1a2e; color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
header h1 { font-size: 1.4rem; font-weight: 600; }
header .meta { font-size: 0.8rem; opacity: 0.7; }
.dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; padding: 24px; max-width: 1400px; margin: 0 auto; }
.card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.card h2 { font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: #444; border-bottom: 2px solid #f0f2f5; padding-bottom: 8px; }
.kpi-card { text-align: center; }
.kpi-value { font-size: 2.5rem; font-weight: 700; color: #1a1a2e; }
.kpi-label { font-size: 0.9rem; color: #888; margin-top: 4px; }
.chart-container { position: relative; height: 280px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { background: #f8f9fa; padding: 8px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #dee2e6; }
td { padding: 8px 12px; border-bottom: 1px solid #f0f2f5; }
tr:hover td { background: #f8f9fa; }
.search-box { width: 100%; padding: 8px; margin-bottom: 12px; border: 1px solid #dee2e6; border-radius: 6px; font-size: 0.85rem; }
"""

_CHART_COLORS = [
    "rgba(79, 129, 189, 0.8)", "rgba(192, 80, 77, 0.8)",
    "rgba(155, 187, 89, 0.8)", "rgba(128, 100, 162, 0.8)",
    "rgba(75, 172, 198, 0.8)", "rgba(247, 150, 70, 0.8)",
]


def _execute_query(conn_id: str, sql: str) -> tuple:
    """쿼리 실행 후 (columns, rows) 반환."""
    from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select, _make_bq_client
    from bi_agent_mcp.config import QUERY_LIMIT, BQ_MAX_BYTES_BILLED

    err = _validate_select(sql)
    if err:
        raise ValueError(err)

    info = _connections.get(conn_id)
    if not info:
        raise ValueError(f"연결 ID '{conn_id}'를 찾을 수 없습니다.")

    if info.db_type == "bigquery":
        from google.cloud.bigquery import QueryJobConfig
        client = _make_bq_client(info)
        job_config = QueryJobConfig(maximum_bytes_billed=BQ_MAX_BYTES_BILLED)
        safe_query = f"SELECT * FROM ({sql}) AS _sub LIMIT {QUERY_LIMIT}"
        rows = list(client.query(safe_query, job_config=job_config).result())
        if not rows:
            return [], []
        columns = list(rows[0].keys())
        return columns, [dict(r) for r in rows]

    conn = _get_conn(info)
    try:
        if info.db_type == "postgresql":
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        safe_query = f"SELECT * FROM ({sql}) AS _sub LIMIT {QUERY_LIMIT}"
        cur.execute(safe_query)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        if info.db_type == "postgresql":
            return columns, [dict(r) for r in rows]
        return columns, list(rows)
    finally:
        conn.close()


def _execute_file_query(file_id: str, sql: str) -> tuple:
    """파일 쿼리 실행 후 (columns, rows) 반환."""
    from bi_agent_mcp.tools.files import _files
    from bi_agent_mcp.tools.db import _validate_select

    err = _validate_select(sql)
    if err:
        raise ValueError(err)

    if file_id not in _files:
        raise ValueError(f"파일 ID '{file_id}'를 찾을 수 없습니다.")

    df = _files[file_id]["df"]
    table_name = _files[file_id]["name"].replace(".", "_").replace("-", "_")

    import duckdb
    con = duckdb.connect()
    con.register("df", df)
    con.register(table_name, df)
    result = con.execute(sql).fetchdf()
    con.close()

    return list(result.columns), result.values.tolist()


def _render_chart(chart_id: str, chart_cfg: dict, columns: list, rows: list) -> str:
    """차트 타입별 HTML 카드 렌더링."""
    title = chart_cfg.get("title", "차트")
    chart_type = chart_cfg.get("type", "bar")

    if not rows:
        return f'<div class="card"><h2>{title}</h2><p style="color:#999;text-align:center;padding:40px">데이터 없음</p></div>'

    # KPI 카드
    if chart_type == "kpi":
        val = rows[0][0] if isinstance(rows[0], (list, tuple)) else list(rows[0].values())[0]
        label = columns[0] if columns else ""
        if isinstance(val, (int, float)):
            display_val = f"{val:,}"
        else:
            display_val = str(val)
        return f'''<div class="card kpi-card">
  <h2>{title}</h2>
  <div class="kpi-value">{display_val}</div>
  <div class="kpi-label">{label}</div>
</div>'''

    # 테이블
    if chart_type == "table":
        headers = "".join(f"<th>{c}</th>" for c in columns)
        body_rows = ""
        for row in rows[:100]:
            vals = row if isinstance(row, (list, tuple)) else list(row.values())
            body_rows += "<tr>" + "".join(f"<td>{v}</td>" for v in vals) + "</tr>"
        return f'''<div class="card" style="grid-column: span 2;">
  <h2>{title}</h2>
  <input class="search-box" type="text" placeholder="검색..." oninput="filterTable(this)">
  <div style="overflow-x:auto"><table><thead><tr>{headers}</tr></thead><tbody>{body_rows}</tbody></table></div>
</div>'''

    # Chart.js 차트 (bar/line/pie)
    labels = []
    datasets = []

    if len(columns) >= 2:
        labels = [str(row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]) for row in rows]
        for i, col in enumerate(columns[1:]):
            data = []
            for row in rows:
                v = row[i+1] if isinstance(row, (list, tuple)) else list(row.values())[i+1]
                try:
                    data.append(float(v) if v is not None else 0)
                except (ValueError, TypeError):
                    data.append(0)
            color = _CHART_COLORS[i % len(_CHART_COLORS)]
            datasets.append({
                "label": col,
                "data": data,
                "backgroundColor": color,
                "borderColor": color.replace("0.8", "1"),
                "borderWidth": 2,
                "tension": 0.3,
                "fill": False,
            })

    chart_data = json.dumps({"labels": labels, "datasets": datasets})
    chart_options = json.dumps({
        "responsive": True,
        "maintainAspectRatio": False,
        "plugins": {"legend": {"position": "top"}},
    })

    return f'''<div class="card">
  <h2>{title}</h2>
  <div class="chart-container">
    <canvas id="{chart_id}"></canvas>
  </div>
  <script>
    new Chart(document.getElementById('{chart_id}'), {{
      type: '{chart_type}',
      data: {chart_data},
      options: {chart_options}
    }});
  </script>
</div>'''


def _build_html(title: str, cards_html: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="{_CHARTJS_CDN}"></script>
  <style>{_DASHBOARD_CSS}</style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <span class="meta">생성: {now} | BI-Agent</span>
  </header>
  <div class="dashboard-grid">
    {cards_html}
  </div>
  <script>
    function filterTable(input) {{
      const filter = input.value.toLowerCase();
      const rows = input.parentElement.querySelectorAll('tbody tr');
      rows.forEach(row => {{
        row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none';
      }});
    }}
  </script>
</body>
</html>"""


def _save_dashboard(html: str, output_path: str, title: str) -> str:
    """대시보드 HTML을 파일로 저장하고 경로를 반환합니다."""
    if output_path:
        path = Path(output_path)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
        path = Path("~/Downloads").expanduser() / f"dashboard_{safe_title}_{ts}.html"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)


def generate_dashboard(
    conn_id: str,
    queries: str,
    title: str = "BI 대시보드",
    save_to_file: bool = False,
    output_path: str = "",
) -> str:
    """[Dashboard] 쿼리 결과를 인터랙티브 HTML 대시보드로 생성합니다.

    Args:
        conn_id: connect_db로 얻은 연결 ID
        queries: JSON 배열 형식의 쿼리 목록.
            예: '[{"sql":"SELECT category,SUM(amount) FROM orders GROUP BY 1","title":"카테고리별 매출","type":"bar"}]'
            type 옵션: "bar"(막대), "line"(선), "pie"(파이), "table"(표), "kpi"(카드)
        title: 대시보드 제목
        save_to_file: True이면 파일로 저장, False이면 HTML 내용만 반환 (기본값: False)
        output_path: 저장 경로 (비우면 ~/Downloads/ 자동 저장, save_to_file=True일 때만 적용)
    """
    try:
        query_list = json.loads(queries)
        if not isinstance(query_list, list):
            query_list = [query_list]
    except json.JSONDecodeError as e:
        return f"[ERROR] queries JSON 파싱 실패: {e}\n예시: '[{{\"sql\": \"SELECT ...\", \"title\": \"제목\", \"type\": \"bar\"}}]'"

    cards = []
    for i, q in enumerate(query_list):
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        sql = q.get("sql", "")
        if not sql:
            continue
        try:
            columns, rows = _execute_query(conn_id, sql)
            cards.append(_render_chart(chart_id, q, columns, rows))
        except Exception as e:
            cards.append(f'<div class="card"><h2>{q.get("title","오류")}</h2><p style="color:red">{e}</p></div>')

    if not cards:
        return "[ERROR] 생성된 차트가 없습니다. queries 파라미터를 확인하세요."

    html = _build_html(title, "\n".join(cards))

    if not save_to_file:
        return f"대시보드 생성 완료 (미리보기)\n차트 수: {len(cards)}개\n\n파일로 저장하려면 save_to_file=True로 다시 호출하세요.\n\n{html}"

    path = _save_dashboard(html, output_path, title)
    return f"[SAVED] 대시보드 저장 완료: {path}\n차트 수: {len(cards)}개\n브라우저에서 파일을 열어 확인하세요."


def chart_from_file(
    file_id: str,
    queries: str,
    title: str = "파일 분석 대시보드",
    save_to_file: bool = False,
    output_path: str = "",
) -> str:
    """[Dashboard] 로드된 파일 데이터로 HTML 대시보드를 생성합니다.

    Args:
        file_id: connect_file로 얻은 파일 ID
        queries: JSON 배열 형식의 쿼리 목록 (테이블명으로 'df' 사용 가능)
        title: 대시보드 제목
        save_to_file: True이면 파일로 저장, False이면 HTML 내용만 반환 (기본값: False)
        output_path: 저장 경로 (save_to_file=True일 때만 적용)
    """
    try:
        query_list = json.loads(queries)
        if not isinstance(query_list, list):
            query_list = [query_list]
    except json.JSONDecodeError as e:
        return f"[ERROR] queries JSON 파싱 실패: {e}"

    cards = []
    for i, q in enumerate(query_list):
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        sql = q.get("sql", "")
        if not sql:
            continue
        try:
            columns, rows = _execute_file_query(file_id, sql)
            cards.append(_render_chart(chart_id, q, columns, rows))
        except Exception as e:
            cards.append(f'<div class="card"><h2>{q.get("title","오류")}</h2><p style="color:red">{e}</p></div>')

    if not cards:
        return "[ERROR] 생성된 차트가 없습니다."

    html = _build_html(title, "\n".join(cards))

    if not save_to_file:
        return f"대시보드 생성 완료 (미리보기)\n차트 수: {len(cards)}개\n\n파일로 저장하려면 save_to_file=True로 다시 호출하세요.\n\n{html}"

    path = _save_dashboard(html, output_path, title)
    return f"[SAVED] 대시보드 저장 완료: {path}\n차트 수: {len(cards)}개"
