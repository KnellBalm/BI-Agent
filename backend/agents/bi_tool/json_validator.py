"""
JSONValidator - InHouse JSON 스키마 검증

Step 15: Final Export의 핵심 컴포넌트
InHouse 표준 스키마 준수 여부를 검증합니다.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json


class ValidationSeverity(Enum):
    """검증 심각도"""
    CRITICAL = "critical"  # 치명적 (스키마 위반)
    ERROR = "error"  # 에러 (필수 필드 누락)
    WARNING = "warning"  # 경고 (권장 필드 누락)


@dataclass
class ValidationError:
    """검증 에러"""
    severity: ValidationSeverity
    path: str  # JSON 경로 (예: "report[0].visual[2].dataModelId")
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "path": self.path,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual
        }


class JSONValidator:
    """
    InHouse JSON 스키마 검증기

    주요 검증 항목:
    1. 필수 필드 존재 여부
    2. 데이터 타입 검증
    3. 참조 무결성 (ID 연결)
    4. 값 범위 검증
    """

    # InHouse JSON 스키마 정의
    SCHEMA = {
        "connector": {
            "required_fields": ["id", "type", "config"],
            "field_types": {
                "id": str,
                "type": str,
                "config": dict
            }
        },
        "datamodel": {
            "required_fields": ["id", "name", "connector_id", "dataset"],
            "field_types": {
                "id": str,
                "name": str,
                "connector_id": str,
                "dataset": dict
            }
        },
        "report": {
            "required_fields": ["id", "name", "visual"],
            "field_types": {
                "id": str,
                "name": str,
                "visual": list,
                "varList": list,
                "eventList": list
            },
            "optional_fields": ["varList", "eventList"]
        },
        "visual": {
            "required_fields": ["id", "type"],
            "field_types": {
                "id": str,
                "type": str,
                "dataModelId": str,
                "style": dict
            },
            "optional_fields": ["dataModelId", "style", "title", "data", "layout"]
        }
    }

    VALID_VISUAL_TYPES = ["bar", "line", "pie", "scatter", "table", "kpi", "text", "image"]
    VALID_CONNECTOR_TYPES = ["postgres", "mysql", "sqlite", "bigquery", "snowflake", "excel"]

    def __init__(self):
        self.errors: List[ValidationError] = []

    def validate(self, json_data: Dict[str, Any]) -> List[ValidationError]:
        """
        전체 JSON 검증

        Args:
            json_data: InHouse JSON 데이터

        Returns:
            ValidationError 리스트
        """
        self.errors = []

        # 최상위 구조 검증
        self._validate_root_structure(json_data)

        # 각 섹션 검증
        if "connector" in json_data:
            self._validate_connectors(json_data["connector"])

        if "datamodel" in json_data:
            self._validate_datamodels(json_data["datamodel"])

        if "report" in json_data:
            self._validate_reports(json_data["report"])

        # 참조 무결성 검증
        self._validate_references(json_data)

        return self.errors

    def _validate_root_structure(self, json_data: Dict[str, Any]):
        """최상위 구조 검증"""
        required_sections = ["connector", "datamodel", "report"]

        for section in required_sections:
            if section not in json_data:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.CRITICAL,
                    path=f"root.{section}",
                    message=f"필수 섹션이 누락되었습니다: {section}",
                    expected="array",
                    actual="missing"
                ))

            elif not isinstance(json_data[section], list):
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.CRITICAL,
                    path=f"root.{section}",
                    message=f"섹션이 배열이 아닙니다: {section}",
                    expected="array",
                    actual=type(json_data[section]).__name__
                ))

    def _validate_connectors(self, connectors: List[Dict[str, Any]]):
        """커넥터 검증"""
        for i, connector in enumerate(connectors):
            path_prefix = f"connector[{i}]"
            schema = self.SCHEMA["connector"]

            # 필수 필드 검증
            for field in schema["required_fields"]:
                if field not in connector:
                    self.errors.append(ValidationError(
                        severity=ValidationSeverity.ERROR,
                        path=f"{path_prefix}.{field}",
                        message=f"필수 필드가 누락되었습니다: {field}",
                        expected=schema["field_types"][field].__name__
                    ))

            # 타입 검증
            connector_type = connector.get("type", "")
            if connector_type not in self.VALID_CONNECTOR_TYPES:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.WARNING,
                    path=f"{path_prefix}.type",
                    message=f"알 수 없는 커넥터 타입입니다: {connector_type}",
                    expected=", ".join(self.VALID_CONNECTOR_TYPES),
                    actual=connector_type
                ))

    def _validate_datamodels(self, datamodels: List[Dict[str, Any]]):
        """데이터 모델 검증"""
        for i, dm in enumerate(datamodels):
            path_prefix = f"datamodel[{i}]"
            schema = self.SCHEMA["datamodel"]

            # 필수 필드 검증
            for field in schema["required_fields"]:
                if field not in dm:
                    self.errors.append(ValidationError(
                        severity=ValidationSeverity.ERROR,
                        path=f"{path_prefix}.{field}",
                        message=f"필수 필드가 누락되었습니다: {field}"
                    ))

            # dataset.query 검증
            dataset = dm.get("dataset", {})
            if not dataset.get("query"):
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    path=f"{path_prefix}.dataset.query",
                    message="쿼리가 비어있습니다.",
                    expected="non-empty string"
                ))

    def _validate_reports(self, reports: List[Dict[str, Any]]):
        """리포트 검증"""
        for i, report in enumerate(reports):
            path_prefix = f"report[{i}]"
            schema = self.SCHEMA["report"]

            # 필수 필드 검증
            for field in schema["required_fields"]:
                if field not in report:
                    self.errors.append(ValidationError(
                        severity=ValidationSeverity.ERROR,
                        path=f"{path_prefix}.{field}",
                        message=f"필수 필드가 누락되었습니다: {field}"
                    ))

            # visual 배열 검증
            visuals = report.get("visual", [])
            self._validate_visuals(visuals, path_prefix)

            # varList/eventList 권장 사항
            if not report.get("varList"):
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.WARNING,
                    path=f"{path_prefix}.varList",
                    message="varList가 없습니다. 인터랙티브 기능을 위해 추가를 권장합니다."
                ))

    def _validate_visuals(self, visuals: List[Dict[str, Any]], parent_path: str):
        """비주얼 컴포넌트 검증"""
        for i, visual in enumerate(visuals):
            path_prefix = f"{parent_path}.visual[{i}]"
            schema = self.SCHEMA["visual"]

            # 필수 필드 검증
            for field in schema["required_fields"]:
                if field not in visual:
                    self.errors.append(ValidationError(
                        severity=ValidationSeverity.ERROR,
                        path=f"{path_prefix}.{field}",
                        message=f"필수 필드가 누락되었습니다: {field}"
                    ))

            # visual type 검증
            visual_type = visual.get("type", "")
            if visual_type not in self.VALID_VISUAL_TYPES:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.WARNING,
                    path=f"{path_prefix}.type",
                    message=f"알 수 없는 visual 타입입니다: {visual_type}",
                    expected=", ".join(self.VALID_VISUAL_TYPES),
                    actual=visual_type
                ))

    def _validate_references(self, json_data: Dict[str, Any]):
        """참조 무결성 검증"""
        # 커넥터 ID 수집
        connector_ids: Set[str] = {
            c.get("id") for c in json_data.get("connector", []) if c.get("id")
        }

        # 데이터 모델 ID 수집
        datamodel_ids: Set[str] = {
            dm.get("id") for dm in json_data.get("datamodel", []) if dm.get("id")
        }

        # 데이터 모델의 connector_id 검증
        for i, dm in enumerate(json_data.get("datamodel", [])):
            connector_id = dm.get("connector_id")
            if connector_id and connector_id not in connector_ids:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    path=f"datamodel[{i}].connector_id",
                    message=f"존재하지 않는 커넥터를 참조합니다: {connector_id}",
                    expected=f"one of {connector_ids}",
                    actual=connector_id
                ))

        # visual의 dataModelId 검증
        for i, report in enumerate(json_data.get("report", [])):
            for j, visual in enumerate(report.get("visual", [])):
                datamodel_id = visual.get("dataModelId")
                if datamodel_id and datamodel_id not in datamodel_ids:
                    self.errors.append(ValidationError(
                        severity=ValidationSeverity.ERROR,
                        path=f"report[{i}].visual[{j}].dataModelId",
                        message=f"존재하지 않는 데이터 모델을 참조합니다: {datamodel_id}",
                        expected=f"one of {datamodel_ids}",
                        actual=datamodel_id
                    ))

    def is_valid(self) -> bool:
        """
        검증 성공 여부

        Returns:
            CRITICAL/ERROR가 없으면 True
        """
        critical_errors = [
            e for e in self.errors
            if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
        ]
        return len(critical_errors) == 0

    def get_summary(self) -> Dict[str, Any]:
        """
        검증 결과 요약

        Returns:
            요약 통계
        """
        critical_count = sum(1 for e in self.errors if e.severity == ValidationSeverity.CRITICAL)
        error_count = sum(1 for e in self.errors if e.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for e in self.errors if e.severity == ValidationSeverity.WARNING)

        return {
            "is_valid": self.is_valid(),
            "total_issues": len(self.errors),
            "critical": critical_count,
            "errors": error_count,
            "warnings": warning_count,
            "compliance_score": self._calculate_compliance_score(critical_count, error_count, warning_count)
        }

    def _calculate_compliance_score(self, critical: int, errors: int, warnings: int) -> int:
        """
        규격 준수 점수 계산 (0-100)

        Args:
            critical: 치명적 에러 수
            errors: 에러 수
            warnings: 경고 수

        Returns:
            점수
        """
        if critical > 0:
            return 0  # 치명적 에러가 있으면 0점

        base_score = 100
        error_penalty = errors * 10
        warning_penalty = warnings * 3

        score = max(0, base_score - error_penalty - warning_penalty)
        return score

    def to_report(self) -> str:
        """
        검증 결과를 읽기 쉬운 텍스트로 변환

        Returns:
            검증 리포트 문자열
        """
        if not self.errors:
            return "✅ 검증 통과: 모든 검사 항목을 만족합니다."

        summary = self.get_summary()
        report_lines = [
            f"📊 InHouse JSON 검증 결과",
            f"",
            f"상태: {'❌ 실패' if not summary['is_valid'] else '⚠️ 경고'}",
            f"규격 준수 점수: {summary['compliance_score']}/100",
            f"",
            f"발견된 이슈:",
            f"  - 치명적: {summary['critical']}개",
            f"  - 에러: {summary['errors']}개",
            f"  - 경고: {summary['warnings']}개",
            f"",
            f"상세 내역:"
        ]

        # 심각도별 정렬
        sorted_errors = sorted(self.errors, key=lambda e: (e.severity.value, e.path))

        for error in sorted_errors:
            severity_icon = {
                ValidationSeverity.CRITICAL: "🔴",
                ValidationSeverity.ERROR: "🟠",
                ValidationSeverity.WARNING: "🟡"
            }[error.severity]

            report_lines.append(f"")
            report_lines.append(f"{severity_icon} [{error.severity.value.upper()}] {error.path}")
            report_lines.append(f"   {error.message}")
            if error.expected:
                report_lines.append(f"   예상: {error.expected}")
            if error.actual:
                report_lines.append(f"   실제: {error.actual}")

        return "\n".join(report_lines)
