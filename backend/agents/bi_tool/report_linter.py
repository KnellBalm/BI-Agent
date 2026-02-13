"""
ReportLinter - 보고서 품질 검사

Step 14: Iterative Refinement의 핵심 컴포넌트
시각적 명료성, 데이터 정확성, 접근성을 검사합니다.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class LintSeverity(Enum):
    """린트 심각도"""
    ERROR = "error"  # 치명적 오류 (반드시 수정)
    WARNING = "warning"  # 경고 (수정 권장)
    INFO = "info"  # 정보성 메시지


@dataclass
class LintIssue:
    """린트 이슈"""
    severity: LintSeverity
    category: str  # "visual", "data", "accessibility", "performance"
    message: str
    component_id: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "component_id": self.component_id,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable
        }


class ReportLinter:
    """
    BI 리포트 품질 검사기

    주요 검사 항목:
    1. 시각적 명료성 (폰트 크기, 대비, 색상)
    2. 데이터 정확성 (참조 무결성, 집계 오류)
    3. 접근성 (색맹 대응, 대체 텍스트)
    4. 성능 (과도한 데이터 포인트)
    """

    # 품질 기준
    MIN_FONT_SIZE = 12
    MAX_COMPONENTS = 15
    MAX_DATA_POINTS_PER_CHART = 1000
    MIN_COLOR_CONTRAST = 4.5  # WCAG AA 기준

    RECOMMENDED_COLORS = {
        "accessible": ["#0077b6", "#00b4d8", "#90e0ef", "#023e8a"],
        "colorblind_safe": ["#0173b2", "#de8f05", "#029e73", "#cc78bc"]
    }

    def __init__(self):
        self.issues: List[LintIssue] = []

    def lint_report(self, report_json: Dict[str, Any]) -> List[LintIssue]:
        """
        전체 리포트 린트 수행

        Args:
            report_json: InHouse JSON 형식의 리포트

        Returns:
            LintIssue 리스트
        """
        self.issues = []

        # 리포트 구조 검증
        if "report" not in report_json or not report_json["report"]:
            self.issues.append(LintIssue(
                severity=LintSeverity.ERROR,
                category="structure",
                message="리포트 섹션이 없습니다.",
                suggestion="report 배열을 추가하세요."
            ))
            return self.issues

        report = report_json["report"][0]

        # 개별 검사 수행
        self._check_visual_clarity(report)
        self._check_data_accuracy(report_json)
        self._check_accessibility(report)
        self._check_performance(report)
        self._check_naming_conventions(report)

        return self.issues

    def _check_visual_clarity(self, report: Dict[str, Any]):
        """시각적 명료성 검사"""
        visuals = report.get("visual", [])

        # 컴포넌트 수 검사
        if len(visuals) > self.MAX_COMPONENTS:
            self.issues.append(LintIssue(
                severity=LintSeverity.WARNING,
                category="visual",
                message=f"컴포넌트가 너무 많습니다 ({len(visuals)}개). 권장: {self.MAX_COMPONENTS}개 이하",
                suggestion="중요하지 않은 컴포넌트를 제거하거나 여러 페이지로 분할하세요."
            ))

        # 각 컴포넌트 검사
        for i, visual in enumerate(visuals):
            component_id = visual.get("id", f"component-{i}")
            style = visual.get("style", {})

            # 폰트 크기 검사
            font_size = style.get("fontSize", 14)
            if isinstance(font_size, str):
                font_size = int(font_size.replace("px", ""))

            if font_size < self.MIN_FONT_SIZE:
                self.issues.append(LintIssue(
                    severity=LintSeverity.WARNING,
                    category="visual",
                    message=f"폰트 크기가 너무 작습니다: {font_size}px (최소 {self.MIN_FONT_SIZE}px)",
                    component_id=component_id,
                    suggestion=f"fontSize를 {self.MIN_FONT_SIZE}px 이상으로 설정하세요.",
                    auto_fixable=True
                ))

            # 제목 검사
            if not visual.get("title") and visual.get("type") not in ["spacer", "divider"]:
                self.issues.append(LintIssue(
                    severity=LintSeverity.INFO,
                    category="visual",
                    message="컴포넌트에 제목이 없습니다.",
                    component_id=component_id,
                    suggestion="사용자가 이해하기 쉽도록 설명적인 제목을 추가하세요."
                ))

    def _check_data_accuracy(self, report_json: Dict[str, Any]):
        """데이터 정확성 검사"""
        datamodels = report_json.get("datamodel", [])
        report = report_json["report"][0]
        visuals = report.get("visual", [])

        # 데이터 모델 ID 수집
        valid_datamodel_ids = {dm.get("id") for dm in datamodels}

        # 참조 무결성 검사
        for i, visual in enumerate(visuals):
            component_id = visual.get("id", f"component-{i}")
            datamodel_id = visual.get("dataModelId")

            if datamodel_id and datamodel_id not in valid_datamodel_ids:
                self.issues.append(LintIssue(
                    severity=LintSeverity.ERROR,
                    category="data",
                    message=f"존재하지 않는 데이터 모델을 참조합니다: {datamodel_id}",
                    component_id=component_id,
                    suggestion="올바른 dataModelId를 지정하거나 해당 데이터 모델을 생성하세요."
                ))

        # 데이터 모델 쿼리 검사
        for dm in datamodels:
            dm_id = dm.get("id", "unknown")
            dataset = dm.get("dataset", {})
            query = dataset.get("query", "")

            # 빈 쿼리 검사
            if not query or query.strip() == "":
                self.issues.append(LintIssue(
                    severity=LintSeverity.ERROR,
                    category="data",
                    message=f"데이터 모델 '{dm_id}'의 쿼리가 비어있습니다.",
                    suggestion="유효한 SQL 쿼리를 작성하세요."
                ))

            # SQL 키워드 검사 (기본적인 검증)
            query_upper = query.upper()
            if "SELECT" not in query_upper:
                self.issues.append(LintIssue(
                    severity=LintSeverity.WARNING,
                    category="data",
                    message=f"데이터 모델 '{dm_id}'의 쿼리가 SELECT 구문을 포함하지 않습니다.",
                    suggestion="올바른 SQL SELECT 쿼리인지 확인하세요."
                ))

    def _check_accessibility(self, report: Dict[str, Any]):
        """접근성 검사"""
        visuals = report.get("visual", [])

        for i, visual in enumerate(visuals):
            component_id = visual.get("id", f"component-{i}")
            style = visual.get("style", {})
            visual_type = visual.get("type", "")

            # 차트에 대체 텍스트 검사
            if visual_type in ["bar", "line", "pie", "scatter"] and not visual.get("altText"):
                self.issues.append(LintIssue(
                    severity=LintSeverity.INFO,
                    category="accessibility",
                    message="차트에 대체 텍스트(altText)가 없습니다.",
                    component_id=component_id,
                    suggestion="스크린 리더 사용자를 위해 차트 내용을 설명하는 altText를 추가하세요."
                ))

            # 색상 대비 검사 (간단한 휴리스틱)
            bg_color = style.get("backgroundColor", "#ffffff")
            text_color = style.get("color", "#000000")

            if bg_color.lower() in ["#ffffff", "#fff", "white"] and text_color.lower() in ["#ffff00", "yellow"]:
                self.issues.append(LintIssue(
                    severity=LintSeverity.WARNING,
                    category="accessibility",
                    message="색상 대비가 낮을 수 있습니다 (흰 배경에 노란 텍스트).",
                    component_id=component_id,
                    suggestion="텍스트 색상을 더 어둡게 변경하세요.",
                    auto_fixable=True
                ))

    def _check_performance(self, report: Dict[str, Any]):
        """성능 검사"""
        visuals = report.get("visual", [])

        for i, visual in enumerate(visuals):
            component_id = visual.get("id", f"component-{i}")

            # 데이터 포인트 수 검사 (data 배열이 있는 경우)
            data = visual.get("data", [])
            if isinstance(data, list) and len(data) > self.MAX_DATA_POINTS_PER_CHART:
                self.issues.append(LintIssue(
                    severity=LintSeverity.WARNING,
                    category="performance",
                    message=f"데이터 포인트가 너무 많습니다: {len(data)}개 (권장: {self.MAX_DATA_POINTS_PER_CHART}개 이하)",
                    component_id=component_id,
                    suggestion="데이터를 집계하거나 페이지네이션을 사용하세요."
                ))

    def _check_naming_conventions(self, report: Dict[str, Any]):
        """명명 규칙 검사"""
        visuals = report.get("visual", [])

        for i, visual in enumerate(visuals):
            component_id = visual.get("id", f"component-{i}")

            # ID 명명 규칙 검사
            if not component_id or component_id.startswith("component-"):
                self.issues.append(LintIssue(
                    severity=LintSeverity.INFO,
                    category="naming",
                    message="컴포넌트 ID가 자동 생성된 기본값입니다.",
                    component_id=component_id,
                    suggestion="의미 있는 ID를 부여하세요 (예: 'sales-trend-chart', 'kpi-revenue')."
                ))

    def get_summary(self) -> Dict[str, Any]:
        """
        린트 결과 요약

        Returns:
            요약 통계
        """
        error_count = sum(1 for issue in self.issues if issue.severity == LintSeverity.ERROR)
        warning_count = sum(1 for issue in self.issues if issue.severity == LintSeverity.WARNING)
        info_count = sum(1 for issue in self.issues if issue.severity == LintSeverity.INFO)

        auto_fixable_count = sum(1 for issue in self.issues if issue.auto_fixable)

        return {
            "total_issues": len(self.issues),
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "auto_fixable": auto_fixable_count,
            "quality_score": self._calculate_quality_score(error_count, warning_count)
        }

    def _calculate_quality_score(self, errors: int, warnings: int) -> int:
        """
        품질 점수 계산 (0-100)

        Args:
            errors: 에러 수
            warnings: 경고 수

        Returns:
            품질 점수
        """
        base_score = 100
        error_penalty = errors * 15
        warning_penalty = warnings * 5

        score = max(0, base_score - error_penalty - warning_penalty)
        return score

    def auto_fix(self, report_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        자동 수정 가능한 이슈 수정

        Args:
            report_json: 원본 리포트 JSON

        Returns:
            수정된 리포트 JSON
        """
        fixed_report = report_json.copy()

        if "report" not in fixed_report or not fixed_report["report"]:
            return fixed_report

        report = fixed_report["report"][0]
        visuals = report.get("visual", [])

        for visual in visuals:
            style = visual.get("style", {})

            # 폰트 크기 자동 수정
            font_size = style.get("fontSize", 14)
            if isinstance(font_size, str):
                font_size = int(font_size.replace("px", ""))

            if font_size < self.MIN_FONT_SIZE:
                style["fontSize"] = f"{self.MIN_FONT_SIZE}px"

            # 색상 대비 자동 수정
            bg_color = style.get("backgroundColor", "#ffffff")
            text_color = style.get("color", "#000000")

            if bg_color.lower() in ["#ffffff", "#fff", "white"] and text_color.lower() in ["#ffff00", "yellow"]:
                style["color"] = "#000000"  # 검정색으로 변경

            visual["style"] = style

        fixed_report["report"][0]["visual"] = visuals

        return fixed_report
