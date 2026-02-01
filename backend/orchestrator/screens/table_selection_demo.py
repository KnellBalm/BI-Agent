"""
Table Selection Screen Demo
Demonstrates usage of TableSelectionScreen with sample data.

Run:
    python -m backend.orchestrator.screens.table_selection_demo
"""

import asyncio
from typing import List

from textual.app import App, ComposeResult
from textual.widgets import Button, Label
from textual.containers import Vertical

from backend.agents.data_source.table_recommender import TableRecommendation, ERDRelationship
from backend.orchestrator.screens.table_selection_screen import TableSelectionScreen


# Sample data for demonstration
SAMPLE_RECOMMENDATIONS = [
    TableRecommendation(
        table_name="sales",
        relevance_score=95,
        explanation_ko="매출 분석에 필수적인 테이블입니다. 매출액, 날짜, 고객ID 등 핵심 지표를 포함합니다.",
        relevant_columns=["sale_id", "amount", "date", "customer_id", "product_id", "quantity"],
        join_suggestions=[
            {"target_table": "customers", "join_column": "customer_id", "target_column": "id"},
            {"target_table": "products", "join_column": "product_id", "target_column": "id"}
        ]
    ),
    TableRecommendation(
        table_name="customers",
        relevance_score=88,
        explanation_ko="고객 세그먼트 분석에 유용합니다. 고객 속성과 인구통계 정보를 제공합니다.",
        relevant_columns=["id", "name", "email", "region", "segment", "registration_date"],
        join_suggestions=[
            {"target_table": "sales", "join_column": "id", "target_column": "customer_id"}
        ]
    ),
    TableRecommendation(
        table_name="products",
        relevance_score=82,
        explanation_ko="제품별 매출 분석에 필요한 제품 마스터 정보를 포함합니다.",
        relevant_columns=["id", "name", "category", "price", "cost", "brand"],
        join_suggestions=[
            {"target_table": "sales", "join_column": "id", "target_column": "product_id"}
        ]
    ),
    TableRecommendation(
        table_name="marketing_campaigns",
        relevance_score=72,
        explanation_ko="마케팅 캠페인 효과 분석에 활용할 수 있습니다.",
        relevant_columns=["campaign_id", "name", "start_date", "end_date", "budget", "channel"],
        join_suggestions=[
            {"target_table": "campaign_responses", "join_column": "campaign_id", "target_column": "campaign_id"}
        ]
    ),
    TableRecommendation(
        table_name="inventory",
        relevance_score=65,
        explanation_ko="재고 수준과 매출의 상관관계 분석에 참고할 수 있습니다.",
        relevant_columns=["product_id", "warehouse_id", "quantity", "last_updated"],
        join_suggestions=[
            {"target_table": "products", "join_column": "product_id", "target_column": "id"}
        ]
    ),
    TableRecommendation(
        table_name="website_logs",
        relevance_score=45,
        explanation_ko="웹 활동 데이터로, 온라인 매출 분석 시 보조적으로 활용 가능합니다.",
        relevant_columns=["timestamp", "user_id", "page_url", "action", "session_id"],
        join_suggestions=[]
    ),
]

SAMPLE_RELATIONSHIPS = [
    ERDRelationship(
        from_table="sales",
        to_table="customers",
        from_column="customer_id",
        to_column="id",
        relationship_type="many-to-one"
    ),
    ERDRelationship(
        from_table="sales",
        to_table="products",
        from_column="product_id",
        to_column="id",
        relationship_type="many-to-one"
    ),
    ERDRelationship(
        from_table="inventory",
        to_table="products",
        from_column="product_id",
        to_column="id",
        relationship_type="many-to-one"
    ),
]


class TableSelectionDemoApp(App):
    """Demo application for TableSelectionScreen."""

    CSS = """
    Screen {
        align: center middle;
        background: #0c0c0e;
    }

    #demo-container {
        width: 60;
        height: auto;
        background: #1a1b1e;
        border: solid #7c3aed;
        padding: 2;
    }

    #demo-title {
        text-align: center;
        color: #7c3aed;
        text-style: bold;
        margin-bottom: 2;
    }

    #demo-description {
        color: #94a3b8;
        margin-bottom: 2;
    }

    #demo-button {
        width: 100%;
        background: #7c3aed;
        color: white;
        margin-top: 1;
    }

    #demo-button:hover {
        background: #6d28d9;
    }

    #result-label {
        color: #10b981;
        margin-top: 2;
        text-align: center;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose demo UI."""
        with Vertical(id="demo-container"):
            yield Label("📊 Table Selection Screen Demo", id="demo-title")

            yield Label(
                "This demo showcases the TableSelectionScreen component.\n\n"
                f"• {len(SAMPLE_RECOMMENDATIONS)} sample table recommendations\n"
                f"• {len(SAMPLE_RELATIONSHIPS)} sample relationships\n"
                "• Interactive multi-select interface\n"
                "• Search and filter functionality\n\n"
                "Click the button below to open the selection screen.",
                id="demo-description"
            )

            yield Button("Launch Table Selection", id="demo-button")

            yield Label("", id="result-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "demo-button":
            self.launch_selection_screen()

    def launch_selection_screen(self) -> None:
        """Launch the table selection screen."""

        def on_tables_selected(selected: List[str]) -> None:
            """Callback when tables are selected."""
            result_label = self.query_one("#result-label", Label)
            if selected:
                result_text = f"✓ Selected {len(selected)} table(s):\n"
                result_text += "\n".join(f"  • {table}" for table in selected)
            else:
                result_text = "No tables selected"

            result_label.update(result_text)

        # Push the table selection screen
        self.push_screen(
            TableSelectionScreen(
                recommendations=SAMPLE_RECOMMENDATIONS,
                relationships=SAMPLE_RELATIONSHIPS,
                callback=on_tables_selected
            )
        )


def run_demo():
    """Run the demo application."""
    app = TableSelectionDemoApp()
    app.run()


if __name__ == "__main__":
    run_demo()
