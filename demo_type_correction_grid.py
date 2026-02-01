#!/usr/bin/env python3
"""
Interactive demo for TypeCorrectionGrid
Run this to see the full interactive UI with type correction suggestions.
"""
import pandas as pd
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer

from backend.agents.data_source.type_corrector import TypeCorrector
from backend.orchestrator.components.data_grid import TypeCorrectionGrid


class TypeCorrectionDemo(App):
    """Textual app to demonstrate TypeCorrectionGrid"""

    TITLE = "Type Correction Grid Demo"
    CSS = """
    Screen {
        background: #0d1117;
    }

    Container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.df = self._create_sample_data()
        self.corrector = TypeCorrector(self.df)
        self.suggestions = self.corrector.suggest_type_corrections()

    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample DataFrame with various type issues"""
        return pd.DataFrame({
            'user_id': ['1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008'],
            'revenue': ['$1,234.56', '$2,345.67', '$3,456.78', '$4,567.89', '$5,678.90', '$6,789.01', '$7,890.12', '$8,901.23'],
            'signup_date': ['2024-01-15', '2024-01-20', '2024-02-05', '2024-02-12', '2024-03-01', '2024-03-15', '2024-04-01', '2024-04-10'],
            'order_count': ['10', '25', '5', '42', '18', '31', '7', '19'],
            'conversion_rate': ['12.5%', '18.3%', '9.7%', '22.1%', '15.4%', '19.8%', '11.2%', '16.7%'],
            'last_login': ['2024-04-30 14:30:00', '2024-04-29 09:15:00', '2024-04-30 18:45:00', '2024-04-28 11:20:00', '2024-04-30 16:00:00', '2024-04-29 13:40:00', '2024-04-30 10:25:00', '2024-04-27 15:50:00'],
            'status': ['active', 'inactive', 'active', 'active', 'pending', 'active', 'inactive', 'active'],
            'lifetime_value': ['15,234', '28,456', '9,876', '52,341', '21,567', '35,890', '12,345', '19,234']
        })

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()

        with Container():
            grid = TypeCorrectionGrid(
                df=self.df,
                sample_size=8
            )
            grid.load_corrections(self.suggestions)
            yield grid

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app"""
        # Display initial notification
        correction_count = len(self.suggestions)
        self.notify(
            f"Found {correction_count} type correction suggestions. Use 'a' to approve, 'r' to reject, Enter to apply.",
            title="Type Corrections Available",
            timeout=5
        )


def main():
    """Run the demo app"""
    print("Starting Type Correction Grid Demo...")
    print("\nKeyboard shortcuts:")
    print("  a / Space    - Approve selected correction")
    print("  r / Delete   - Reject selected correction")
    print("  ↑ / ↓        - Navigate corrections")
    print("  Enter        - Apply all approved corrections")
    print("  q            - Quit")
    print("\n" + "="*60 + "\n")

    app = TypeCorrectionDemo()
    app.run()


if __name__ == "__main__":
    main()
