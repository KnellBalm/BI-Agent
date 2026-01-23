import xml.etree.ElementTree as ET
import os
from typing import Optional

# Import the new schema engine for integration
try:
    from .tableau_meta_schema import TableauMetaSchemaEngine, TableauMetaJSON
except ImportError:
    # Fallback if running standalone
    from tableau_meta_schema import TableauMetaSchemaEngine, TableauMetaJSON


class TableauMetadataEngine:
    """
    Tableau .twb (XML) 파일을 분석하고 수정하는 엔진

    Enhanced with Meta JSON conversion support via TableauMetaSchemaEngine integration.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tree = None
        self.root = None
        if os.path.exists(file_path):
            self.load()

    def load(self):
        """XML 파일을 로드합니다."""
        self.tree = ET.parse(self.file_path)
        self.root = self.tree.getroot()

    def save(self, output_path: str = None):
        """수정된 XML을 저장합니다."""
        path = output_path or self.file_path
        self.tree.write(path, encoding="utf-8", xml_declaration=True)

    def update_field_caption(self, field_name: str, new_caption: str) -> bool:
        """
        특정 필드의 캡션(시스템 이름 대신 사용자에게 보일 이름)을 수정합니다.
        XML 내 <column name='[field_name]' caption='...' /> 구조를 찾습니다.
        """
        if self.root is None:
            return False

        found = False
        # 모든 column 태그 탐색
        for column in self.root.iter('column'):
            if column.get('name') == f"[{field_name}]" or column.get('name') == field_name:
                column.set('caption', new_caption)
                found = True

        return found

    def get_datasource_names(self):
        """파일에 포함된 데이터 원본 목록을 반환합니다."""
        return [ds.get('name') for ds in self.root.iter('datasource')]

    def to_meta_json(self) -> TableauMetaJSON:
        """
        Convert current .twb file to Meta JSON format

        Returns:
            TableauMetaJSON object containing structured metadata

        Example:
            >>> engine = TableauMetadataEngine("myworkbook.twb")
            >>> meta_json = engine.to_meta_json()
            >>> meta_json.save("output.json")
        """
        schema_engine = TableauMetaSchemaEngine(self.file_path)
        return schema_engine.to_meta_json()

    @staticmethod
    def create_empty_meta() -> TableauMetaJSON:
        """
        Create an empty Meta JSON template

        Returns:
            Empty TableauMetaJSON object

        Example:
            >>> empty = TableauMetadataEngine.create_empty_meta()
            >>> print(empty.to_json())
        """
        return TableauMetaSchemaEngine.create_empty_meta()

# 테스트용 Mock XML 생성 함수
def create_mock_twb(path: str):
    root = ET.Element("workbook")
    datasources = ET.SubElement(root, "datasources")
    ds = ET.SubElement(datasources, "datasource", name="SalesData")
    ET.SubElement(ds, "column", name="[OrderDate]", caption="주문일자")
    ET.SubElement(ds, "column", name="[Sales]", caption="매출액")
    
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
