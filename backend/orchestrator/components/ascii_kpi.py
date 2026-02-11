"""
ASCIIKPICard - TUI 내 ASCII 기반 KPI 카드 위젯

Step 13: Draft Briefing의 핵심 컴포넌트
Rich 라이브러리를 사용하여 스파크라인을 포함한 KPI 카드를 렌더링합니다.
"""

from typing import List, Optional, Dict, Any
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.columns import Columns
from rich.console import Group


class ASCIIKPICard:
    """
    ASCII 기반 KPI 카드 생성기

    주요 기능:
    1. 단일 KPI 값 표시 (큰 폰트)
    2. 증감률 (델타) 표시
    3. 스파크라인 미니 차트
    4. 색상 코딩 (긍정/부정/중립)
    """

    # 스파크라인용 유니코드 문자
    SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"

    @staticmethod
    def create_card(
        label: str,
        value: str,
        delta: Optional[str] = None,
        trend_data: Optional[List[float]] = None,
        color: str = "cyan",
        unit: Optional[str] = None,
        width: int = 24
    ) -> Panel:
        """
        단일 KPI 카드 생성

        Args:
            label: KPI 라벨 (예: "총 매출")
            value: KPI 값 (예: "1.2M", "95%")
            delta: 증감률 (예: "+5%", "-2.3%")
            trend_data: 트렌드 데이터 (스파크라인용)
            color: 카드 색상 (cyan, green, yellow, red, magenta)
            unit: 단위 (예: "원", "%", "건")
            width: 카드 너비

        Returns:
            Rich Panel 객체
        """
        content = Text()

        # 값 표시 (큰 폰트 효과)
        value_text = f"{value}"
        if unit:
            value_text = f"{value}{unit}"

        content.append(f"{value_text}\n", style=f"bold {color}")

        # 델타 표시
        if delta:
            delta_color = "green" if delta.startswith("+") else "red" if delta.startswith("-") else "yellow"
            content.append(f"{delta}\n", style=f"bold {delta_color}")

        # 스파크라인 표시
        if trend_data:
            sparkline = ASCIIKPICard.generate_sparkline(trend_data)
            content.append(f"{sparkline}\n", style="dim")

        # 카드 생성
        card = Panel(
            Align.center(content, vertical="middle"),
            title=f"[bold]{label}[/bold]",
            border_style=color,
            width=width,
            padding=(1, 2)
        )

        return card

    @staticmethod
    def generate_sparkline(values: List[float], max_length: int = 20) -> str:
        """
        스파크라인 생성

        Args:
            values: 숫자 값 리스트
            max_length: 최대 표시 길이

        Returns:
            스파크라인 문자열
        """
        if not values:
            return ""

        # 최근 max_length개만 사용
        recent_values = values[-max_length:]

        # 정규화
        v_min = min(recent_values)
        v_max = max(recent_values)
        v_range = v_max - v_min if v_max != v_min else 1

        # 스파크라인 생성
        sparkline = ""
        for v in recent_values:
            normalized = (v - v_min) / v_range
            idx = int(normalized * (len(ASCIIKPICard.SPARKLINE_CHARS) - 1))
            sparkline += ASCIIKPICard.SPARKLINE_CHARS[idx]

        return sparkline

    @staticmethod
    def create_kpi_grid(kpis: List[Dict[str, Any]], columns: int = 3) -> Columns:
        """
        여러 KPI 카드를 그리드로 배치

        Args:
            kpis: KPI 정보 딕셔너리 리스트
                  각 항목: {"label": str, "value": str, "delta": str, "trend_data": List[float], "color": str}
            columns: 컬럼 수

        Returns:
            Rich Columns 객체
        """
        cards = []

        for kpi in kpis:
            card = ASCIIKPICard.create_card(
                label=kpi.get("label", "Unknown"),
                value=kpi.get("value", "0"),
                delta=kpi.get("delta"),
                trend_data=kpi.get("trend_data"),
                color=kpi.get("color", "cyan"),
                unit=kpi.get("unit")
            )
            cards.append(card)

        return Columns(cards, equal=True, expand=True)

    @staticmethod
    def create_detailed_card(
        label: str,
        main_value: str,
        sub_metrics: List[Dict[str, str]],
        trend_data: Optional[List[float]] = None,
        color: str = "cyan",
        width: int = 40
    ) -> Panel:
        """
        상세 정보를 포함한 KPI 카드 생성

        Args:
            label: KPI 라벨
            main_value: 메인 값
            sub_metrics: 서브 지표 리스트 [{"label": "평균", "value": "100"}]
            trend_data: 트렌드 데이터
            color: 색상
            width: 너비

        Returns:
            Rich Panel 객체
        """
        # 메인 값
        main_text = Text()
        main_text.append(f"{main_value}\n\n", style=f"bold {color}")

        # 스파크라인
        if trend_data:
            sparkline = ASCIIKPICard.generate_sparkline(trend_data)
            main_text.append(f"{sparkline}\n\n", style="dim")

        # 서브 지표 테이블
        sub_table = Table(show_header=False, box=None, padding=(0, 1))

        for metric in sub_metrics:
            sub_table.add_row(
                Text(metric.get("label", ""), style="dim"),
                Text(metric.get("value", ""), style="bold white")
            )

        # 그룹으로 결합
        content = Group(
            Align.center(main_text, vertical="top"),
            sub_table
        )

        card = Panel(
            content,
            title=f"[bold]{label}[/bold]",
            border_style=color,
            width=width,
            padding=(1, 2)
        )

        return card

    @staticmethod
    def create_comparison_card(
        label: str,
        current_value: str,
        previous_value: str,
        delta_percent: float,
        trend_data: Optional[List[float]] = None,
        width: int = 30
    ) -> Panel:
        """
        비교 KPI 카드 (현재 vs 이전)

        Args:
            label: KPI 라벨
            current_value: 현재 값
            previous_value: 이전 값
            delta_percent: 증감률 (%)
            trend_data: 트렌드 데이터
            width: 너비

        Returns:
            Rich Panel 객체
        """
        # 증감 방향에 따른 색상
        if delta_percent > 0:
            color = "green"
            arrow = "↑"
        elif delta_percent < 0:
            color = "red"
            arrow = "↓"
        else:
            color = "yellow"
            arrow = "→"

        content = Text()

        # 현재 값
        content.append(f"{current_value}\n", style=f"bold {color}")

        # 증감률
        delta_str = f"{arrow} {abs(delta_percent):.1f}%"
        content.append(f"{delta_str}\n", style=f"bold {color}")

        # 이전 값 (작게)
        content.append(f"이전: {previous_value}\n", style="dim")

        # 스파크라인
        if trend_data:
            sparkline = ASCIIKPICard.generate_sparkline(trend_data)
            content.append(f"{sparkline}", style="dim")

        card = Panel(
            Align.center(content, vertical="middle"),
            title=f"[bold]{label}[/bold]",
            border_style=color,
            width=width,
            padding=(1, 2)
        )

        return card


# 사용 예시
if __name__ == "__main__":
    from rich.console import Console

    console = Console()

    # 단일 카드
    card1 = ASCIIKPICard.create_card(
        label="총 매출",
        value="1.2M",
        delta="+15.3%",
        trend_data=[100, 120, 115, 130, 125, 140, 150, 145, 160, 170],
        color="green",
        unit="원"
    )

    # 여러 KPI 그리드
    kpis = [
        {
            "label": "총 매출",
            "value": "1,234,567",
            "delta": "+15.3%",
            "trend_data": [100, 120, 115, 130, 125, 140, 150],
            "color": "green",
            "unit": "원"
        },
        {
            "label": "주문 수",
            "value": "456",
            "delta": "-2.1%",
            "trend_data": [50, 48, 52, 49, 47, 45, 46],
            "color": "red",
            "unit": "건"
        },
        {
            "label": "전환율",
            "value": "3.4",
            "delta": "+0.5%",
            "trend_data": [3.0, 3.1, 3.2, 3.3, 3.4],
            "color": "cyan",
            "unit": "%"
        }
    ]

    grid = ASCIIKPICard.create_kpi_grid(kpis, columns=3)

    # 상세 카드
    detailed = ASCIIKPICard.create_detailed_card(
        label="월별 매출",
        main_value="₩5,678,900",
        sub_metrics=[
            {"label": "평균", "value": "₩189,296"},
            {"label": "최대", "value": "₩450,000"},
            {"label": "최소", "value": "₩89,000"}
        ],
        trend_data=[150, 180, 170, 200, 190, 220, 250, 240, 270, 290],
        color="magenta"
    )

    # 비교 카드
    comparison = ASCIIKPICard.create_comparison_card(
        label="이번 달 매출",
        current_value="₩3,456,789",
        previous_value="₩3,000,000",
        delta_percent=15.2,
        trend_data=[2800000, 2900000, 2850000, 3000000, 3100000, 3200000, 3456789]
    )

    # 출력
    console.print("\n[bold cyan]단일 KPI 카드[/bold cyan]")
    console.print(card1)

    console.print("\n[bold cyan]KPI 그리드[/bold cyan]")
    console.print(grid)

    console.print("\n[bold cyan]상세 KPI 카드[/bold cyan]")
    console.print(detailed)

    console.print("\n[bold cyan]비교 KPI 카드[/bold cyan]")
    console.print(comparison)
