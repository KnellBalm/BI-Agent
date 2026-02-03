"""
Tableau Meta JSON Schema Definition and Conversion Engine

This module defines the standard JSON schema for Tableau metadata
and provides conversion utilities between .twb XML and Meta JSON format.
"""

import json
import xml.etree.ElementTree as XET
try:
    import defusedxml.ElementTree as ET
except ImportError:
    ET = XET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FieldMeta:
    """Represents a field in the datasource"""
    name: str
    type: str  # "string", "date", "number", "boolean"
    role: str  # "dimension", "measure"
    aggregation: Optional[str] = None  # "SUM", "AVG", "COUNT", "MIN", "MAX"
    caption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "type": self.type,
            "role": self.role
        }
        if self.aggregation:
            result["aggregation"] = self.aggregation
        if self.caption:
            result["caption"] = self.caption
        return result


@dataclass
class ConnectionMeta:
    """Represents a datasource connection"""
    type: str  # "postgres", "mysql", "excel", "snowflake", etc.
    table: Optional[str] = None
    database: Optional[str] = None
    server: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.table:
            result["table"] = self.table
        if self.database:
            result["database"] = self.database
        if self.server:
            result["server"] = self.server
        return result


@dataclass
class DatasourceMeta:
    """Represents a datasource with its fields"""
    name: str
    connection: ConnectionMeta
    fields: List[FieldMeta]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "connection": self.connection.to_dict(),
            "fields": [f.to_dict() for f in self.fields]
        }


@dataclass
class CalculatedFieldMeta:
    """Represents a calculated field"""
    name: str
    formula: str
    type: str  # "string", "date", "number", "boolean"
    role: str  # "dimension", "measure"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "formula": self.formula,
            "type": self.type,
            "role": self.role
        }


@dataclass
class WorksheetMeta:
    """Represents a worksheet with visualizations"""
    name: str
    visual_type: str  # "bar", "line", "pie", "table", "scatter", etc.
    dimensions: List[str]
    measures: List[str]
    filters: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "visual_type": self.visual_type,
            "dimensions": self.dimensions,
            "measures": self.measures
        }
        if self.filters:
            result["filters"] = self.filters
        return result


@dataclass
class TableauMetaJSON:
    """Top-level Tableau metadata JSON structure"""
    version: str
    tool: str
    datasources: List[DatasourceMeta]
    worksheets: List[WorksheetMeta]
    calculated_fields: List[CalculatedFieldMeta]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "tool": self.tool,
            "datasources": [ds.to_dict() for ds in self.datasources],
            "worksheets": [ws.to_dict() for ws in self.worksheets],
            "calculated_fields": [cf.to_dict() for cf in self.calculated_fields]
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, file_path: str):
        """Save to JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


class TableauMetaSchemaEngine:
    """
    Enhanced Tableau Metadata Engine with Meta JSON conversion support

    Extends the existing TableauMetadataEngine to support:
    1. Converting .twb XML to Meta JSON format
    2. Creating empty Meta JSON templates
    3. Parsing and extracting structured metadata from Tableau workbooks
    """

    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize the engine

        Args:
            file_path: Optional path to .twb file. If None, works with empty templates.
        """
        self.file_path = file_path
        self.tree = None
        self.root = None

        if file_path and Path(file_path).exists():
            self._load_xml()

    def _load_xml(self):
        """Load XML file from disk"""
        self.tree = ET.parse(self.file_path)
        self.root = self.tree.getroot()

    def to_meta_json(self) -> TableauMetaJSON:
        """
        Convert loaded .twb XML to Meta JSON format

        Returns:
            TableauMetaJSON object containing parsed metadata
        """
        if self.root is None:
            raise ValueError("No XML loaded. Call _load_xml() or provide file_path.")

        # Extract datasources
        datasources = self._extract_datasources()

        # Extract worksheets
        worksheets = self._extract_worksheets()

        # Extract calculated fields
        calculated_fields = self._extract_calculated_fields()

        return TableauMetaJSON(
            version="1.0",
            tool="tableau",
            datasources=datasources,
            worksheets=worksheets,
            calculated_fields=calculated_fields
        )

    def _extract_datasources(self) -> List[DatasourceMeta]:
        """Extract datasource metadata from XML"""
        datasources = []

        for ds_elem in self.root.iter('datasource'):
            ds_name = ds_elem.get('name')
            if not ds_name or ds_name == 'Parameters':
                continue

            # Extract connection info
            connection = self._extract_connection(ds_elem)

            # Extract fields
            fields = self._extract_fields(ds_elem)

            datasources.append(DatasourceMeta(
                name=ds_name,
                connection=connection,
                fields=fields
            ))

        return datasources

    def _extract_connection(self, ds_elem: XET.Element) -> ConnectionMeta:
        """Extract connection metadata from datasource element"""
        connection_elem = ds_elem.find('.//connection')

        if connection_elem is not None:
            conn_class = connection_elem.get('class', 'unknown')

            # Map Tableau connection class to simple type
            type_mapping = {
                'postgres': 'postgres',
                'mysql': 'mysql',
                'excel': 'excel',
                'snowflake': 'snowflake',
                'bigquery': 'bigquery',
                'sqlserver': 'sqlserver'
            }

            conn_type = 'unknown'
            for key, value in type_mapping.items():
                if key in conn_class.lower():
                    conn_type = value
                    break

            return ConnectionMeta(
                type=conn_type,
                table=connection_elem.get('table'),
                database=connection_elem.get('dbname'),
                server=connection_elem.get('server')
            )

        # Default connection if not specified
        return ConnectionMeta(type='unknown')

    def _extract_fields(self, ds_elem: XET.Element) -> List[FieldMeta]:
        """Extract field metadata from datasource element"""
        fields = []

        for column_elem in ds_elem.findall('.//column'):
            field_name = column_elem.get('name', '')

            # Clean up field name (remove brackets)
            clean_name = field_name.strip('[]')

            # Skip system fields
            if clean_name.startswith('Measure Names') or clean_name.startswith('Number of Records'):
                continue

            # Determine field type from datatype attribute
            datatype = column_elem.get('datatype', 'string')
            type_mapping = {
                'string': 'string',
                'integer': 'number',
                'real': 'number',
                'date': 'date',
                'datetime': 'date',
                'boolean': 'boolean'
            }
            field_type = type_mapping.get(datatype, 'string')

            # Determine role (dimension vs measure)
            role = column_elem.get('role', 'dimension')

            # Extract aggregation if present
            aggregation = None
            if role == 'measure':
                type_attr = column_elem.get('type')
                if type_attr and type_attr.startswith('quantitative'):
                    aggregation = 'SUM'  # Default aggregation

            # Extract caption
            caption = column_elem.get('caption')

            fields.append(FieldMeta(
                name=clean_name,
                type=field_type,
                role=role,
                aggregation=aggregation,
                caption=caption
            ))

        return fields

    def _extract_worksheets(self) -> List[WorksheetMeta]:
        """Extract worksheet metadata from XML"""
        worksheets = []

        for ws_elem in self.root.iter('worksheet'):
            ws_name = ws_elem.get('name', 'Unnamed')

            # Determine visual type from marks
            visual_type = self._determine_visual_type(ws_elem)

            # Extract dimensions and measures from rows/columns
            dimensions, measures = self._extract_dimensions_measures(ws_elem)

            # Extract filters
            filters = self._extract_filters(ws_elem)

            worksheets.append(WorksheetMeta(
                name=ws_name,
                visual_type=visual_type,
                dimensions=dimensions,
                measures=measures,
                filters=filters if filters else None
            ))

        return worksheets

    def _determine_visual_type(self, ws_elem: XET.Element) -> str:
        """Determine visualization type from worksheet element"""
        # Look for mark type in the worksheet
        mark_elem = ws_elem.find('.//mark')
        if mark_elem is not None:
            mark_class = mark_elem.get('class', 'automatic')

            # Map Tableau mark types to simple visual types
            type_mapping = {
                'bar': 'bar',
                'line': 'line',
                'circle': 'scatter',
                'square': 'table',
                'pie': 'pie',
                'area': 'area',
                'text': 'table',
                'automatic': 'bar'  # default
            }

            for key, value in type_mapping.items():
                if key in mark_class.lower():
                    return value

        return 'table'  # Default to table if unknown

    def _extract_dimensions_measures(self, ws_elem: XET.Element) -> tuple[List[str], List[str]]:
        """Extract dimensions and measures from worksheet rows/columns"""
        dimensions = []
        measures = []

        # Extract from rows
        rows_elem = ws_elem.find('.//rows')
        if rows_elem is not None:
            dimensions.extend(self._parse_shelf_fields(rows_elem, 'dimension'))
            measures.extend(self._parse_shelf_fields(rows_elem, 'measure'))

        # Extract from columns
        cols_elem = ws_elem.find('.//cols')
        if cols_elem is not None:
            dimensions.extend(self._parse_shelf_fields(cols_elem, 'dimension'))
            measures.extend(self._parse_shelf_fields(cols_elem, 'measure'))

        return dimensions, measures

    def _parse_shelf_fields(self, shelf_elem: XET.Element, field_role: str) -> List[str]:
        """Parse field names from a shelf element (rows/cols)"""
        fields = []

        # Simple heuristic: look for field references in the text
        shelf_text = shelf_elem.text or ''

        # Extract field names within brackets
        import re
        matches = re.findall(r'\[([^\]]+)\]', shelf_text)

        # Filter by role if needed (this is simplified)
        fields.extend([m for m in matches if m and not m.startswith('Measure Names')])

        return fields

    def _extract_filters(self, ws_elem: ET.Element) -> List[Dict[str, Any]]:
        """Extract filter metadata from worksheet"""
        filters = []

        for filter_elem in ws_elem.findall('.//filter'):
            field_name = filter_elem.get('column', '')
            clean_name = field_name.strip('[]')

            if clean_name:
                filters.append({
                    "field": clean_name,
                    "type": "simple"  # Simplified for MVP
                })

        return filters

    def _extract_calculated_fields(self) -> List[CalculatedFieldMeta]:
        """Extract calculated field metadata from XML"""
        calc_fields = []

        for column_elem in self.root.iter('column'):
            # Check if this is a calculated field (has formula)
            calc_elem = column_elem.find('.//calculation')

            if calc_elem is not None and calc_elem.get('formula'):
                field_name = column_elem.get('name', '').strip('[]')
                formula = calc_elem.get('formula', '')
                datatype = column_elem.get('datatype', 'string')
                role = column_elem.get('role', 'measure')

                # Map datatype
                type_mapping = {
                    'string': 'string',
                    'integer': 'number',
                    'real': 'number',
                    'date': 'date',
                    'boolean': 'boolean'
                }
                field_type = type_mapping.get(datatype, 'string')

                calc_fields.append(CalculatedFieldMeta(
                    name=field_name,
                    formula=formula,
                    type=field_type,
                    role=role
                ))

        return calc_fields

    @staticmethod
    def create_empty_meta() -> TableauMetaJSON:
        """
        Create an empty Meta JSON template

        Returns:
            Empty TableauMetaJSON object with sample structure
        """
        return TableauMetaJSON(
            version="1.0",
            tool="tableau",
            datasources=[],
            worksheets=[],
            calculated_fields=[]
        )

    @staticmethod
    def create_sample_meta() -> TableauMetaJSON:
        """
        Create a sample Meta JSON for testing/demo purposes

        Returns:
            Sample TableauMetaJSON with example sales data
        """
        return TableauMetaJSON(
            version="1.0",
            tool="tableau",
            datasources=[
                DatasourceMeta(
                    name="SalesData",
                    connection=ConnectionMeta(
                        type="postgres",
                        table="sales",
                        database="analytics",
                        server="localhost:5433"
                    ),
                    fields=[
                        FieldMeta(
                            name="OrderDate",
                            type="date",
                            role="dimension",
                            caption="주문일자"
                        ),
                        FieldMeta(
                            name="Sales",
                            type="number",
                            role="measure",
                            aggregation="SUM",
                            caption="매출액"
                        ),
                        FieldMeta(
                            name="Category",
                            type="string",
                            role="dimension",
                            caption="카테고리"
                        ),
                        FieldMeta(
                            name="Quantity",
                            type="number",
                            role="measure",
                            aggregation="SUM",
                            caption="수량"
                        )
                    ]
                )
            ],
            worksheets=[
                WorksheetMeta(
                    name="Monthly Sales",
                    visual_type="bar",
                    dimensions=["OrderDate"],
                    measures=["Sales"],
                    filters=None
                ),
                WorksheetMeta(
                    name="Category Analysis",
                    visual_type="table",
                    dimensions=["Category"],
                    measures=["Sales", "Quantity"],
                    filters=None
                )
            ],
            calculated_fields=[
                CalculatedFieldMeta(
                    name="Profit Margin",
                    formula="SUM([Profit]) / SUM([Sales])",
                    type="number",
                    role="measure"
                )
            ]
        )


# Helper function for easy conversion
def twb_to_meta_json(twb_path: str, output_path: Optional[str] = None) -> TableauMetaJSON:
    """
    Convert a .twb file to Meta JSON

    Args:
        twb_path: Path to input .twb file
        output_path: Optional path to save JSON file

    Returns:
        TableauMetaJSON object
    """
    engine = TableauMetaSchemaEngine(twb_path)
    meta_json = engine.to_meta_json()

    if output_path:
        meta_json.save(output_path)

    return meta_json


if __name__ == "__main__":
    # Example usage
    print("Tableau Meta JSON Schema Engine")
    print("=" * 50)

    # Create sample meta JSON
    sample = TableauMetaSchemaEngine.create_sample_meta()
    print("\nSample Meta JSON:")
    print(sample.to_json())

    # Test with existing test.twb if available
    test_twb_path = "/Users/zokr/python_workspace/BI-Agent/tmp/test.twb"
    if Path(test_twb_path).exists():
        print("\n" + "=" * 50)
        print(f"Converting {test_twb_path} to Meta JSON:")
        print("=" * 50)

        engine = TableauMetaSchemaEngine(test_twb_path)
        meta_json = engine.to_meta_json()
        print(meta_json.to_json())
