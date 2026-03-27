"""[Helper] 시각화 방법 안내 및 대시보드 설계 가이드 도구."""


def _detect_column_types(columns: list) -> dict:
    """컬럼명을 분석해 시계열/범주형/수치형 분류."""
    time_keywords = {"date", "time", "month", "year", "week", "day", "hour", "dt"}
    category_keywords = {"category", "type", "status", "name", "region", "channel", "product", "brand", "group"}

    time_cols = [c for c in columns if any(k in c.lower() for k in time_keywords)]
    cat_cols = [c for c in columns if any(k in c.lower() for k in category_keywords)]
    num_cols = [c for c in columns if c not in time_cols and c not in cat_cols]

    return {"time": time_cols, "category": cat_cols, "numeric": num_cols}


def _recommend_chart_type(col_types: dict) -> tuple:
    """컬럼 타입 분석 결과로 권장 차트 타입과 배치 설명 반환."""
    if col_types["time"]:
        chart = "Line"
        reason = "시계열 컬럼이 있어 추이 분석에 적합한 Line 차트를 권장합니다."
        x = col_types["time"][0]
        y = col_types["numeric"][0] if col_types["numeric"] else "(수치 컬럼)"
    elif col_types["category"]:
        chart = "Bar"
        reason = "범주형 컬럼이 있어 그룹 비교에 적합한 Bar 차트를 권장합니다."
        x = col_types["category"][0]
        y = col_types["numeric"][0] if col_types["numeric"] else "(수치 컬럼)"
    elif len(col_types["numeric"]) >= 2:
        chart = "Scatter"
        reason = "수치 컬럼이 2개 이상이어서 상관관계 분석에 적합한 Scatter 차트를 권장합니다."
        x = col_types["numeric"][0]
        y = col_types["numeric"][1]
    else:
        chart = "Text"
        reason = "시계열/범주/수치 구분이 어려워 Table(Text) 형식을 권장합니다."
        x = "(컬럼 선택 필요)"
        y = "(컬럼 선택 필요)"

    return chart, reason, x, y


def visualize_advisor(
    data_columns: list,
    analysis_goal: str,
    output_format: str = "auto",
) -> str:
    """[Helper] 데이터 컬럼과 분석 목표에 맞는 최적 시각화 방법을 종합 안내합니다.

    generate_dashboard(Chart.js HTML)와 generate_twbx(Tableau TWBX) 중
    어떤 도구를 쓸지, 어떤 차트 타입이 적합한지, 데이터를 어떻게 배치할지 안내합니다.

    Args:
        data_columns: 사용 가능한 컬럼명 목록. 예: ["date", "revenue", "category"]
        analysis_goal: 분석 목표. 예: "월별 매출 추이", "카테고리별 비교", "두 수치 상관관계"
        output_format: "auto" | "dashboard" | "tableau"
            - "auto": 데이터와 목표로 자동 판단
            - "dashboard": generate_dashboard(Chart.js HTML) 위주
            - "tableau": generate_twbx(Tableau TWBX) 위주
    """
    col_types = _detect_column_types(data_columns)
    chart_type, chart_reason, x_col, y_col = _recommend_chart_type(col_types)

    # 출력 도구 선택
    use_dashboard = False
    use_tableau = False
    tool_reason = ""

    if output_format == "dashboard":
        use_dashboard = True
        tool_reason = "output_format='dashboard'로 지정되어 generate_dashboard를 사용합니다."
    elif output_format == "tableau":
        use_tableau = True
        tool_reason = "output_format='tableau'로 지정되어 generate_twbx를 사용합니다."
    else:
        # auto 판단
        if len(data_columns) >= 4:
            use_dashboard = True
            tool_reason = "컬럼이 4개 이상으로 인터랙티브 웹 대시보드(generate_dashboard)가 적합합니다."
        else:
            use_dashboard = True
            use_tableau = True
            tool_reason = "두 도구 모두 사용 가능합니다. 웹 공유가 목적이면 generate_dashboard, 깊은 분석이 목적이면 generate_twbx를 선택하세요."

    # 컬럼 타입 분석 요약
    col_analysis_lines = []
    if col_types["time"]:
        col_analysis_lines.append(f"- 시계열 컬럼: {', '.join(col_types['time'])}")
    if col_types["category"]:
        col_analysis_lines.append(f"- 범주형 컬럼: {', '.join(col_types['category'])}")
    if col_types["numeric"]:
        col_analysis_lines.append(f"- 수치형 컬럼: {', '.join(col_types['numeric'])}")
    if not col_analysis_lines:
        col_analysis_lines.append("- 컬럼 타입 자동 분류 불가 — 직접 지정 권장")

    col_analysis = "\n".join(col_analysis_lines)

    # 도구 호출 예시 구성
    chart_type_lower = chart_type.lower()
    example_parts = []

    if use_dashboard:
        example_parts.append(
            f'# generate_dashboard 예시\n'
            f'queries = \'[{{"sql": "SELECT {x_col}, {y_col} FROM your_table", '
            f'"title": "{analysis_goal}", "type": "{chart_type_lower}"}}]\'\n'
            f'result = generate_dashboard(conn_id="<연결ID>", queries=queries, title="{analysis_goal}")'
        )

    if use_tableau:
        example_parts.append(
            f'# generate_twbx 예시\n'
            f'result = generate_twbx(\n'
            f'    data="...마크다운 테이블...",\n'
            f'    chart_type="{chart_type}",\n'
            f'    title="{analysis_goal}"\n'
            f')'
        )

    examples_block = "\n\n".join(example_parts)

    return (
        f"## 시각화 방법 추천: {analysis_goal}\n\n"
        f"### 권장 출력 도구\n"
        f"{tool_reason}\n\n"
        f"### 차트 타입\n"
        f"{col_analysis}\n\n"
        f"{chart_reason}\n"
        f"권장 차트 타입: **{chart_type}**\n\n"
        f"### 데이터 배치\n"
        f"- X축: `{x_col}`\n"
        f"- Y축: `{y_col}`\n\n"
        f"### 도구 호출 예시\n"
        f"```python\n{examples_block}\n```"
    )


def dashboard_design_guide(
    kpi_metrics: list,
    dimension_cols: list,
    time_col: str = "",
) -> str:
    """[Helper] KPI와 차원 컬럼 기반으로 generate_dashboard 호출용 레이아웃을 설계합니다.

    Args:
        kpi_metrics: KPI로 표시할 수치형 컬럼 목록. 예: ["revenue", "orders", "conversion_rate"]
        dimension_cols: 분류/그룹 기준 컬럼 목록. 예: ["category", "region", "channel"]
        time_col: 시계열 컬럼명. 예: "date" (없으면 "")
    """
    charts_lines = []

    # KPI 카드
    for kpi in kpi_metrics:
        charts_lines.append(
            f'    {{"sql": "SELECT SUM({kpi}) AS {kpi} FROM your_table", '
            f'"title": "{kpi} 합계", "type": "kpi"}},'
        )

    # 주요 차트: 시계열 있으면 line, 없으면 bar
    if time_col and kpi_metrics:
        main_kpi = kpi_metrics[0]
        charts_lines.append(
            f'    {{"sql": "SELECT {time_col}, SUM({main_kpi}) AS {main_kpi} FROM your_table GROUP BY {time_col} ORDER BY {time_col}", '
            f'"title": "시계열 추이 ({main_kpi})", "type": "line"}},'
        )
        main_chart_desc = f"- 주요 차트: `{time_col}` × `{main_kpi}` → **Line** 차트 (시계열 추이)"
    elif dimension_cols and kpi_metrics:
        dim = dimension_cols[0]
        main_kpi = kpi_metrics[0]
        charts_lines.append(
            f'    {{"sql": "SELECT {dim}, SUM({main_kpi}) AS {main_kpi} FROM your_table GROUP BY {dim} ORDER BY {main_kpi} DESC", '
            f'"title": "{dim}별 {main_kpi}", "type": "bar"}},'
        )
        main_chart_desc = f"- 주요 차트: `{dim}` × `{main_kpi}` → **Bar** 차트 (그룹 비교)"
    else:
        main_chart_desc = "- 주요 차트: 시계열/차원 컬럼이 없어 테이블 형식 권장"

    # 보조 차트: 나머지 dimension_cols
    sub_chart_descs = []
    for dim in dimension_cols[1:]:
        if kpi_metrics:
            kpi = kpi_metrics[0]
            charts_lines.append(
                f'    {{"sql": "SELECT {dim}, SUM({kpi}) AS {kpi} FROM your_table GROUP BY {dim}", '
                f'"title": "{dim}별 {kpi}", "type": "bar"}},'
            )
            sub_chart_descs.append(f"- 보조 차트: `{dim}` × `{kpi}` → **Bar** 차트")

    if not sub_chart_descs:
        sub_chart_descs.append("- 보조 차트: 추가 dimension_cols 없음")

    kpi_card_desc = f"- KPI 카드: {', '.join(f'`{k}`' for k in kpi_metrics)} → 각각 숫자 카드"
    sub_charts_block = "\n".join(sub_chart_descs)
    charts_code = "\n".join(charts_lines).rstrip(",")

    title_example = "BI 대시보드"

    return (
        f"## 대시보드 설계 가이드\n\n"
        f"### 권장 차트 조합\n"
        f"{kpi_card_desc}\n"
        f"{main_chart_desc}\n"
        f"{sub_charts_block}\n\n"
        f"### generate_dashboard 호출 방법\n"
        f"```python\n"
        f"# generate_dashboard 파라미터:\n"
        f"# conn_id: connect_db로 얻은 연결 ID\n"
        f"# queries: JSON 배열 형식의 쿼리 목록 (type: bar/line/pie/table/kpi)\n"
        f"# title: 대시보드 제목\n"
        f"import json\n\n"
        f"queries = json.dumps([\n"
        f"{charts_code}\n"
        f"])\n"
        f'result = generate_dashboard(conn_id="<연결ID>", queries=queries, title="{title_example}")\n'
        f"```\n\n"
        f"### 레이아웃 팁\n"
        f"- KPI 카드를 상단에 배치해 핵심 수치를 한눈에 확인\n"
        f"- 중요도 순으로 차트 배치 (시계열 추이 → 그룹 비교 → 세부 분석)\n"
        f"- 같은 계열 색상을 KPI별로 통일해 가독성 향상\n"
        f"- 차트 수는 6개 이하로 유지해 대시보드 집중도 확보"
    )
