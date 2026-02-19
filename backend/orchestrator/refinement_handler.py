"""
RefinementHandler - 실시간 수정 명령 처리

Step 14: Iterative Refinement의 핵심 컴포넌트
사용자의 수정 명령을 파싱하고 리포트를 업데이트합니다.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from backend.orchestrator.providers.llm_provider import LLMProvider


@dataclass
class RefinementCommand:
    """수정 명령 구조"""
    command_type: str  # "change_chart", "add_filter", "change_color", "reorder", "remove"
    target_component: Optional[str] = None  # 대상 컴포넌트 ID
    parameters: Dict[str, Any] = None  # 수정 파라미터
    original_text: str = ""  # 원본 사용자 입력

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class RefinementHandler:
    """
    사용자의 수정 명령을 처리하는 핸들러

    주요 기능:
    1. 자연어 수정 명령 파싱
    2. 명령 타입 분류 (차트 변경, 필터 추가 등)
    3. 리포트 JSON 업데이트
    4. 변경 이력 추적
    """

    COMMAND_PATTERNS = {
        # 차트 타입 변경
        "change_chart": [
            r"차트.*?([가-힣]+).*?바꿔",
            r"([가-힣]+).*?차트로.*?변경",
            r"(bar|line|pie|scatter).*?chart",
            r"그래프.*?([가-힣]+).*?수정"
        ],
        # 필터 추가
        "add_filter": [
            r"필터.*?추가",
            r"([가-힣]+).*?제외",
            r"([가-힣]+).*?만.*?보여",
            r"filter.*?add"
        ],
        # 색상 변경
        "change_color": [
            r"색.*?바꿔",
            r"([가-힣]+)색으로",
            r"color.*?change",
            r"테마.*?변경"
        ],
        # 순서 변경
        "reorder": [
            r"순서.*?바꿔",
            r"([가-힣]+).*?앞으로",
            r"([가-힣]+).*?뒤로",
            r"reorder"
        ],
        # 제거
        "remove": [
            r"삭제",
            r"제거",
            r"빼",
            r"없애",
            r"remove",
            r"delete"
        ]
    }

    CHART_TYPE_MAPPING = {
        "막대": "bar",
        "바": "bar",
        "선": "line",
        "라인": "line",
        "파이": "pie",
        "원": "pie",
        "산점도": "scatter",
        "scatter": "scatter",
        "테이블": "table",
        "표": "table"
    }

    REFINEMENT_PROMPT_TEMPLATE = """당신은 BI 리포트 수정 명령 파서입니다. 사용자의 자연어 명령을 구조화된 수정 명령으로 변환하세요.

**사용자 명령**: "{user_command}"

**현재 리포트 구조**:
```json
{report_structure}
```

**과업**:
사용자의 명령을 분석하여 다음 정보를 추출하세요:

1. **command_type**: 명령 타입
   - "change_chart": 차트 타입 변경
   - "add_filter": 필터 추가
   - "change_color": 색상/테마 변경
   - "reorder": 컴포넌트 순서 변경
   - "remove": 컴포넌트 제거
   - "update_data": 데이터 업데이트

2. **target_component**: 대상 컴포넌트 ID (예: "chart-1", "kpi-card-2")

3. **parameters**: 수정 파라미터
   - change_chart: {{"new_chart_type": "bar|line|pie|scatter|table"}}
   - add_filter: {{"field": "컬럼명", "operator": "=|>|<|!=", "value": "값"}}
   - change_color: {{"color_scheme": "blue|green|red|purple"}}
   - reorder: {{"new_position": 숫자}}
   - remove: {{}}

**출력 형식** (JSON):
{{
    "command_type": "change_chart",
    "target_component": "chart-1",
    "parameters": {{
        "new_chart_type": "line"
    }},
    "confidence": 0.95,
    "explanation_ko": "사용자가 첫 번째 차트를 라인 차트로 변경하고자 합니다."
}}

JSON만 반환하고 추가 텍스트는 생략하세요."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        """
        Args:
            llm: LLM 공급자 (선택적, 없으면 규칙 기반 파싱)
        """
        self.llm = llm
        self.change_history: List[Dict[str, Any]] = []

    def parse_command(self, user_input: str, report_structure: Optional[Dict] = None) -> RefinementCommand:
        """
        사용자 명령 파싱

        Args:
            user_input: 사용자 입력 텍스트
            report_structure: 현재 리포트 구조 (LLM 파싱용)

        Returns:
            RefinementCommand 객체
        """
        # LLM 사용 가능하면 LLM 파싱
        if self.llm and report_structure:
            return self._parse_with_llm(user_input, report_structure)

        # Fallback: 규칙 기반 파싱
        return self._parse_with_rules(user_input)

    def _parse_with_rules(self, user_input: str) -> RefinementCommand:
        """
        규칙 기반 명령 파싱

        Args:
            user_input: 사용자 입력

        Returns:
            RefinementCommand 객체
        """
        user_input_lower = user_input.lower()

        # 명령 타입 감지
        detected_type = "unknown"
        for cmd_type, patterns in self.COMMAND_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    detected_type = cmd_type
                    break
            if detected_type != "unknown":
                break

        # 파라미터 추출
        parameters = {}

        if detected_type == "change_chart":
            # 차트 타입 추출
            for korean, english in self.CHART_TYPE_MAPPING.items():
                if korean in user_input or english in user_input_lower:
                    parameters["new_chart_type"] = english
                    break

        elif detected_type == "add_filter":
            # 간단한 필터 파싱 (예: "서울만 보여줘")
            # 실제로는 더 정교한 파싱 필요
            parameters["filter_hint"] = user_input

        elif detected_type == "change_color":
            # 색상 키워드 추출
            colors = ["blue", "green", "red", "purple", "orange", "pink"]
            for color in colors:
                if color in user_input_lower or f"{color}색" in user_input:
                    parameters["color_scheme"] = color
                    break

        # 대상 컴포넌트 추출 (숫자 기반)
        component_match = re.search(r'(\d+)번째', user_input)
        if component_match:
            idx = int(component_match.group(1)) - 1
            target_component = f"component-{idx}"
        else:
            # 첫 번째 차트/컴포넌트로 가정
            target_component = "chart-0"

        return RefinementCommand(
            command_type=detected_type,
            target_component=target_component,
            parameters=parameters,
            original_text=user_input
        )

    async def _parse_with_llm(self, user_input: str, report_structure: Dict) -> RefinementCommand:
        """
        LLM 기반 명령 파싱

        Args:
            user_input: 사용자 입력
            report_structure: 리포트 구조

        Returns:
            RefinementCommand 객체
        """
        import json

        prompt = self.REFINEMENT_PROMPT_TEMPLATE.format(
            user_command=user_input,
            report_structure=json.dumps(report_structure, ensure_ascii=False, indent=2)
        )

        try:
            response = await self.llm.generate(prompt, max_tokens=500)

            # JSON 추출
            json_str = self._extract_json(response)
            parsed = json.loads(json_str)

            return RefinementCommand(
                command_type=parsed.get("command_type", "unknown"),
                target_component=parsed.get("target_component"),
                parameters=parsed.get("parameters", {}),
                original_text=user_input
            )

        except Exception as e:
            # Fallback to rule-based
            return self._parse_with_rules(user_input)

    def _extract_json(self, text: str) -> str:
        """JSON 추출"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]

        return text

    def apply_command(
        self,
        command: RefinementCommand,
        report_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        수정 명령을 리포트 JSON에 적용

        Args:
            command: 수정 명령
            report_json: 원본 리포트 JSON

        Returns:
            업데이트된 리포트 JSON
        """
        updated_report = report_json.copy()

        if command.command_type == "change_chart":
            updated_report = self._apply_chart_change(command, updated_report)

        elif command.command_type == "add_filter":
            updated_report = self._apply_filter_add(command, updated_report)

        elif command.command_type == "change_color":
            updated_report = self._apply_color_change(command, updated_report)

        elif command.command_type == "reorder":
            updated_report = self._apply_reorder(command, updated_report)

        elif command.command_type == "remove":
            updated_report = self._apply_remove(command, updated_report)

        # 변경 이력 추가
        self.change_history.append({
            "command": command.original_text,
            "type": command.command_type,
            "target": command.target_component,
            "parameters": command.parameters
        })

        return updated_report

    def _apply_chart_change(self, command: RefinementCommand, report: Dict) -> Dict:
        """차트 타입 변경 적용"""
        new_type = command.parameters.get("new_chart_type")
        if not new_type:
            return report

        # report["visual"] 내에서 대상 컴포넌트 찾기
        if "report" in report and len(report["report"]) > 0:
            visuals = report["report"][0].get("visual", [])
            for visual in visuals:
                if visual.get("id") == command.target_component:
                    visual["type"] = new_type
                    break

        return report

    def _apply_filter_add(self, command: RefinementCommand, report: Dict) -> Dict:
        """필터 추가 적용"""
        # varList에 필터 변수 추가
        if "report" in report and len(report["report"]) > 0:
            var_list = report["report"][0].get("varList", [])

            new_var = {
                "id": f"filter-{len(var_list)}",
                "name": command.parameters.get("filter_hint", "custom_filter"),
                "type": "parameter",
                "value": command.parameters.get("value", "")
            }
            var_list.append(new_var)
            report["report"][0]["varList"] = var_list

        return report

    def _apply_color_change(self, command: RefinementCommand, report: Dict) -> Dict:
        """색상 변경 적용"""
        color_scheme = command.parameters.get("color_scheme")
        if not color_scheme:
            return report

        # 모든 visual의 style.color 업데이트
        if "report" in report and len(report["report"]) > 0:
            visuals = report["report"][0].get("visual", [])
            for visual in visuals:
                if "style" not in visual:
                    visual["style"] = {}
                visual["style"]["primaryColor"] = color_scheme

        return report

    def _apply_reorder(self, command: RefinementCommand, report: Dict) -> Dict:
        """컴포넌트 순서 변경 적용"""
        new_position = command.parameters.get("new_position", 0)

        if "report" in report and len(report["report"]) > 0:
            visuals = report["report"][0].get("visual", [])

            # 대상 컴포넌트 찾기
            target_idx = None
            for i, visual in enumerate(visuals):
                if visual.get("id") == command.target_component:
                    target_idx = i
                    break

            if target_idx is not None and 0 <= new_position < len(visuals):
                # 위치 변경
                item = visuals.pop(target_idx)
                visuals.insert(new_position, item)
                report["report"][0]["visual"] = visuals

        return report

    def _apply_remove(self, command: RefinementCommand, report: Dict) -> Dict:
        """컴포넌트 제거 적용"""
        if "report" in report and len(report["report"]) > 0:
            visuals = report["report"][0].get("visual", [])

            # 대상 컴포넌트 제거
            report["report"][0]["visual"] = [
                v for v in visuals if v.get("id") != command.target_component
            ]

        return report

    def get_change_history(self) -> List[Dict[str, Any]]:
        """변경 이력 반환"""
        return self.change_history

    def undo_last_change(self) -> bool:
        """
        마지막 변경 취소 (향후 구현)

        Returns:
            성공 여부
        """
        if not self.change_history:
            return False

        # TODO: 실제 undo 로직 구현
        self.change_history.pop()
        return True
