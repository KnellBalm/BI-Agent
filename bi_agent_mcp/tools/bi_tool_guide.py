"""[Helper] BI 툴 시각화 가이드 — 차트/계산/기능/트러블슈팅 단계별 안내."""
from __future__ import annotations

_SUPPORTED_TOOLS = {"tableau", "powerbi", "quicksight", "looker"}

_TOOL_DOCS: dict[str, str] = {
    "tableau": "https://help.tableau.com/current/pro/desktop/en-us/",
    "powerbi": "https://learn.microsoft.com/en-us/power-bi/",
    "quicksight": "https://docs.aws.amazon.com/quicksight/latest/user/",
    "looker": "https://support.google.com/looker-studio/",
}


def bi_tool_guide(
    intent: str,
    columns: str = "",
    tool: str = "",
    situation: str = "",
) -> str:
    """[Helper] BI 툴 시각화 가이드.

    tool 미지정 → 차트 타입 추천 + 4개 툴 비교
    tool 지정   → 5개 모드(차트/계산/기능/트러블슈팅) 중 적합한 가이드 반환
    매핑 안 됨  → 폴백 가이드 반환 (에러 아님)

    Args:
        intent: 필수. "월별 매출 추이를 보고 싶다", "고객별 최초구매일 구하기"
        columns: 선택. "date, revenue, region" 또는 JSON
        tool: 선택. "tableau" / "powerbi" / "quicksight" / "looker"
        situation: 선택. 트러블슈팅 키워드. "연결 오류", "함수 오류"
    """
    if not intent or not intent.strip():
        return "[ERROR] intent는 필수 파라미터입니다. 예: '월별 매출 추이를 보고 싶다'"

    tool_lower = tool.strip().lower()
    if tool_lower and tool_lower not in _SUPPORTED_TOOLS:
        return (
            f"[ERROR] 지원하지 않는 툴입니다: '{tool}'. "
            "tool은 tableau / powerbi / quicksight / looker 중 하나여야 합니다."
        )

    if not tool_lower:
        return _mode_recommend(intent.strip(), columns.strip())

    return _dispatch(intent.strip(), columns.strip(), tool_lower, situation.strip())


def _dispatch(intent: str, columns: str, tool: str, situation: str) -> str:
    """모드 분기 — 추후 구현."""
    return f"## {tool.upper()} 가이드\n\n(구현 중)"


def _mode_recommend(intent: str, columns: str) -> str:
    """추천 모드 — 추후 구현."""
    return "## 추천\n\n(구현 중)"
