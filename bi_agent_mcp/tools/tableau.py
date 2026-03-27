"""
Tableau 시각화용 통합 패키지(.twbx) 생성 도구.
"""
import csv
import logging
import re
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _detect_column_type(values: list) -> str:
    """샘플 값으로 컬럼 타입 추론. 'date', 'measure', 'dimension' 반환."""
    date_pattern = re.compile(r'^\d{4}[-/]\d{2}([-/]\d{2})?$')
    numeric_pattern = re.compile(r'^-?\d+(\.\d+)?$')

    non_empty = [str(v).strip() for v in values if v and str(v).strip() not in ('', 'None', 'null')]
    if not non_empty:
        return 'dimension'

    date_count = sum(1 for v in non_empty if date_pattern.match(v))
    numeric_count = sum(1 for v in non_empty if numeric_pattern.match(v))

    if date_count / len(non_empty) > 0.7:
        return 'date'
    if numeric_count / len(non_empty) > 0.7:
        return 'measure'
    return 'dimension'


def _determine_chart_layout(col_types: dict) -> tuple[str, list, list]:
    """컬럼 타입 기반 차트 타입, columns_shelf, rows_shelf 반환."""
    dates = [c for c, t in col_types.items() if t == 'date']
    measures = [c for c, t in col_types.items() if t == 'measure']
    dimensions = [c for c, t in col_types.items() if t == 'dimension']

    if dates and measures:
        return 'line', dates[:1], measures[:1]
    elif dimensions and measures:
        return 'bar', dimensions[:1], measures[:1]
    elif len(measures) >= 2:
        return 'scatter', measures[:1], measures[1:2]
    else:
        return 'text', list(col_types.keys())[:2], []


def _parse_markdown_table(md_table_str: str) -> tuple[list[str], list[list[str]]]:
    """
    마크다운 포맷의 테이블 문자열을 (headers, rows) 튜플로 변환합니다.
    """
    headers = []
    rows = []
    lines = md_table_str.strip().split("\n")
    first_row = True
    for line in lines:
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue

        # 컬럼 분리 (앞뒤 여백 제거)
        cols = [c.strip() for c in line.strip("|").split("|")]

        # 구분선(---) 스킵: :---:, ---: 등 포함
        if all(set(c.replace(":", "").replace("-", "")) == set() for c in cols if c):
            continue

        if first_row:
            headers = cols
            first_row = False
        else:
            rows.append(cols)

    return headers, rows


def generate_twbx(
    query_result: str = "",
    chart_type: str = "auto",
    title: str = "TWBX Report",
    data: str = "",
) -> str:
    """[Export] 마크다운 포맷의 데이터를 CSV와 연동된 Tableau Workbook 패키지(.twbx)로 자동 생성합니다.
    생성된 파일은 홈 디렉토리의 Downloads 폴더에 저장됩니다.

    Args:
        query_result: 데이터 (마크다운 테이블 포맷 문자열) - 하위 호환용
        data: 데이터 (마크다운 테이블 포맷 문자열) - query_result 대체
        chart_type: 생성할 차트 종류 ("auto", "Bar", "Line", "Scatter", "Text" 등). "auto"이면 데이터 타입 자동 감지
        title: 저장될 워크북 및 시트 이름

    Returns:
        최종 생성된 TWBX 파일 절대 경로 메시지
    """
    # data 파라미터 우선, 없으면 query_result 사용
    input_data = data if data else query_result

    # 1. 마크다운 테이블 파싱
    headers, data_rows = _parse_markdown_table(input_data)
    if not headers or not data_rows:
        return "[ERROR] 마크다운 테이블 포맷이 유효하지 않거나 데이터가 없습니다."

    # 차트 유형 결정
    mark_mapping = {
        "bar": "Bar",
        "line": "Line",
        "scatter": "Shape",
        "heatmap": "Square",
        "text": "Text",
    }

    if chart_type.lower() == "auto":
        # 각 컬럼의 값으로 타입 감지
        col_types = {}
        for i, header in enumerate(headers):
            col_values = [row[i] for row in data_rows if i < len(row)]
            col_types[header] = _detect_column_type(col_values)
        auto_chart, columns_shelf, rows_shelf = _determine_chart_layout(col_types)
        mark_type = mark_mapping.get(auto_chart, "Bar")
    else:
        mark_type = mark_mapping.get(chart_type.lower(), "Bar")
        col_types = {}
        for i, header in enumerate(headers):
            col_values = [row[i] for row in data_rows if i < len(row)]
            col_types[header] = _detect_column_type(col_values)
        _, columns_shelf, rows_shelf = _determine_chart_layout(col_types)
    
    # 작업에 쓸 유일 ID 생성
    job_id = str(uuid.uuid4())[:8]
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    
    temp_dir = Path.home() / f".bi-agent-mcp/temp_{job_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 2. CSV 파일 기록 위치 생성 (TWBX 압축 구조: Data/Datasources/ 혹은 Data/Extracts/)
        data_dir = temp_dir / "Data" / "Extracts"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "data.csv"
        
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data_rows)
            
        # 3. shelf 바인딩 XML 조각 생성
        columns_fields_xml = ""
        for col_field in columns_shelf:
            columns_fields_xml += f"        <column-instance column='[{col_field}]' derivation='None' name='[{col_field}]' pivot='key' type='nominal' />\n"

        rows_fields_xml = ""
        for row_field in rows_shelf:
            rows_fields_xml += f"        <column-instance column='[{row_field}]' derivation='Sum' name='SUM([{row_field}])' pivot='key' type='quantitative' />\n"

        # mark_type을 Tableau style encoding 값으로 변환
        style_mark_type_mapping = {
            "Bar": "bar",
            "Line": "line",
            "Shape": "circle",
            "Square": "square",
            "Text": "text",
        }
        style_mark_type = style_mark_type_mapping.get(mark_type, "bar")

        # 4. 최소한의 유효한 .twb (XML) 템플릿 파일 생성
        # 주의: Tableau XML 형식은 버전과 구조에 민감하므로 가장 기본적인 통용 버전을 사용
        twb_content = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2021.2.0' source-platform='mac' version='18.1' xml:base='https://public.tableau.com' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
    <datasource caption='data' inline='true' name='federated.1' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='data' name='textscan.1'>
            <connection class='textscan' directory='Data/Extracts' filename='data.csv' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.1' name='data.csv' table='[data#csv]' type='table' />
      </connection>
    </datasource>
  </datasources>
  <worksheets>
    <worksheet name='{title}'>
      <layout-options>
        <title>
          <formatted-text>
            <run>{title}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource name='federated.1' />
          </datasources>
          <columns-fields>
{columns_fields_xml}          </columns-fields>
          <rows-fields>
{rows_fields_xml}          </rows-fields>
        </view>
        <style>
          <style-rule element='mark'>
            <encoding attr='type'>
              <nominal value='{style_mark_type}' />
            </encoding>
          </style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark_type}' />
          </pane>
        </panes>
        <rows />
        <cols />
      </table>
    </worksheet>
  </worksheets>
</workbook>
"""
        twb_path = temp_dir / "workbook.twb"
        with open(twb_path, "w", encoding="utf-8") as f:
            f.write(twb_content)
            
        # 4. ZIP 압축하여 .twbx 파일 생성
        download_dir = Path.home() / "Downloads"
        if not download_dir.exists():
            download_dir = Path.home()
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = download_dir / f"{safe_title}_{timestamp}.twbx"
        
        with zipfile.ZipFile(final_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # zip 파일 내부에 workbook.twb 추가
            zipf.write(twb_path, arcname="workbook.twb")
            # zip 파일 내부에 Data/Extracts/data.csv 추가
            zipf.write(csv_path, arcname="Data/Extracts/data.csv")
            
        return f"[SUCCESS] Tableau TWBX 패키지 생성 완료: {final_file}"
        
    except Exception as e:
        logger.error(f"TWBX 생성 중 오류: {e}")
        return f"[ERROR] TWBX 파일 생성에 실패했습니다: {e}"
        
    finally:
        # 임시 디렉토리 정리
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
