"""
Constraint Input Screen for BI-Agent
Provides UI for inputting analysis constraints (date ranges, categorical filters, free-text)
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Callable
from datetime import date, datetime

from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Checkbox, Static
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.app import ComposeResult
from textual.binding import Binding

from backend.utils.logger_setup import setup_logger

logger = setup_logger("constraint_screen", "constraint_screen.log")


@dataclass
class DateRangeConstraint:
    """Date range constraint with validation."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def validate(self) -> bool:
        """Validate that start_date <= end_date if both are set."""
        if self.start_date and self.end_date:
            return self.start_date <= self.end_date
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class CategoricalConstraint:
    """Categorical constraint for a specific field."""
    field: str  # "region", "category", etc.
    selected_values: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "selected_values": self.selected_values
        }


@dataclass
class AnalysisConstraints:
    """Complete set of analysis constraints."""
    date_range: Optional[DateRangeConstraint] = None
    categorical: List[CategoricalConstraint] = field(default_factory=list)
    free_text: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "date_range": self.date_range.to_dict() if self.date_range else None,
            "categorical": [c.to_dict() for c in self.categorical],
            "free_text": self.free_text
        }

    def is_empty(self) -> bool:
        """Check if all constraints are empty."""
        return (
            (not self.date_range or (not self.date_range.start_date and not self.date_range.end_date)) and
            not self.categorical and
            not self.free_text
        )


class ConstraintScreen(ModalScreen):
    """
    Modal screen for inputting analysis constraints.

    Features:
    - Date range picker (start/end dates)
    - Categorical multi-select (region, category, etc.)
    - Free-text constraint input
    - Validation
    """

    CSS = '''
    ConstraintScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #constraint-modal {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #1a1b1e;
        border: solid #7c3aed;
        padding: 1 2;
    }

    #constraint-title {
        color: #7c3aed;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    #constraint-help {
        color: #6b7280;
        text-align: center;
        margin-bottom: 1;
    }

    .section {
        margin: 1 0;
        padding: 1;
        border: solid #2d2f34;
        background: #111214;
    }

    .section-title {
        color: #7c3aed;
        text-style: bold;
        margin-bottom: 1;
    }

    .date-row {
        margin: 0 0 1 0;
    }

    .date-label {
        width: 25;
        color: #9ca3af;
    }

    #date-start, #date-end {
        width: 30;
    }

    .field-label {
        color: #9ca3af;
        margin: 1 0 0 0;
    }

    .checkbox-container {
        margin-left: 2;
    }

    #free-text {
        width: 100%;
        margin-top: 1;
    }

    .button-row {
        margin-top: 2;
        align: center middle;
    }

    #confirm-btn {
        background: #22c55e;
        color: white;
        margin: 0 1;
    }

    #confirm-btn:hover {
        background: #16a34a;
    }

    #cancel-btn {
        background: #ef4444;
        color: white;
        margin: 0 1;
    }

    #cancel-btn:hover {
        background: #dc2626;
    }

    .error-message {
        color: #ef4444;
        text-style: bold;
        margin-top: 1;
        text-align: center;
    }
    '''

    BINDINGS = [
        Binding("y,enter", "confirm", "Confirm", priority=True),
        Binding("n,escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        available_fields: Optional[Dict[str, List[str]]] = None,
        callback: Optional[Callable[[AnalysisConstraints], None]] = None
    ):
        """
        Initialize constraint screen.

        Args:
            available_fields: Dictionary mapping field names to possible values
            callback: Function to call with collected constraints
        """
        super().__init__()
        self.available_fields = available_fields or {}
        self.callback = callback
        self.checkboxes: Dict[str, List[Checkbox]] = {}
        logger.info(f"ConstraintScreen initialized with {len(self.available_fields)} fields")

    def compose(self) -> ComposeResult:
        """Compose the UI elements."""
        with Container(id="constraint-modal"):
            yield Label("분석 제약 조건 입력", id="constraint-title")
            yield Label(
                "[dim]Tab: 다음 필드 | Y/Enter: 승인 | N/Esc: 취소[/dim]",
                id="constraint-help"
            )

            with VerticalScroll():
                # Date range section
                with Container(classes="section"):
                    yield Label("📅 날짜 범위", classes="section-title")
                    with Horizontal(classes="date-row"):
                        yield Label("시작일 (YYYY-MM-DD):", classes="date-label")
                        yield Input(
                            id="date-start",
                            placeholder="2024-01-01",
                            value=""
                        )
                    with Horizontal(classes="date-row"):
                        yield Label("종료일 (YYYY-MM-DD):", classes="date-label")
                        yield Input(
                            id="date-end",
                            placeholder="2024-12-31",
                            value=""
                        )

                # Categorical constraints section
                if self.available_fields:
                    with Container(classes="section"):
                        yield Label("🏷️ 범주형 필터", classes="section-title")

                        for field_name, values in self.available_fields.items():
                            yield Label(f"{field_name}:", classes="field-label")

                            # Limit to 10 options per field to avoid UI clutter
                            display_values = values[:10]

                            with Vertical(classes="checkbox-container"):
                                for value in display_values:
                                    checkbox_id = f"check_{field_name}_{value}"
                                    checkbox = Checkbox(
                                        str(value),
                                        id=checkbox_id,
                                        value=False
                                    )
                                    yield checkbox

                                    # Track checkboxes by field
                                    if field_name not in self.checkboxes:
                                        self.checkboxes[field_name] = []
                                    self.checkboxes[field_name].append(checkbox)

                            if len(values) > 10:
                                yield Label(
                                    f"[dim]... 및 {len(values) - 10}개 더 (처음 10개만 표시)[/dim]",
                                    classes="field-label"
                                )

                # Free-text constraints
                with Container(classes="section"):
                    yield Label("✏️ 추가 제약 조건", classes="section-title")
                    yield Input(
                        id="free-text",
                        placeholder="추가 제약 조건을 입력하세요 (쉼표로 구분)",
                        value=""
                    )

            # Error message placeholder
            yield Static("", id="error-message", classes="error-message")

            # Buttons
            with Horizontal(classes="button-row"):
                yield Button("[Y] 승인", id="confirm-btn", variant="success")
                yield Button("[N] 취소", id="cancel-btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            self.action_confirm()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_confirm(self) -> None:
        """Collect and validate constraints, then call callback."""
        logger.info("User confirming constraints")

        # Clear previous error
        error_label = self.query_one("#error-message", Static)
        error_label.update("")

        # Collect all constraints
        constraints = self._collect_constraints()

        # Validate
        validation_error = self._validate_constraints(constraints)
        if validation_error:
            logger.warning(f"Constraint validation failed: {validation_error}")
            error_label.update(f"❌ {validation_error}")
            self.notify(validation_error, severity="error", timeout=3)
            return

        logger.info(f"Constraints validated successfully: {constraints.to_dict()}")

        # Call callback if provided
        if self.callback:
            self.callback(constraints)

        # Dismiss with the constraints as result
        self.dismiss(constraints)

    def action_cancel(self) -> None:
        """Cancel and dismiss the screen."""
        logger.info("User cancelled constraint input")
        self.dismiss(None)

    def _collect_constraints(self) -> AnalysisConstraints:
        """Collect all constraint values from UI elements."""
        logger.debug("Collecting constraints from UI")

        # Collect date range
        start_str = self.query_one("#date-start", Input).value.strip()
        end_str = self.query_one("#date-end", Input).value.strip()

        date_range = None
        if start_str or end_str:
            date_range = DateRangeConstraint(
                start_date=self._parse_date(start_str) if start_str else None,
                end_date=self._parse_date(end_str) if end_str else None
            )
            logger.debug(f"Date range collected: {date_range}")

        # Collect categorical constraints
        categorical = []
        for field_name, checkboxes in self.checkboxes.items():
            selected = []
            for checkbox in checkboxes:
                if checkbox.value:  # Checkbox is checked
                    # Extract value from checkbox label
                    selected.append(checkbox.label.plain)

            if selected:
                categorical.append(CategoricalConstraint(
                    field=field_name,
                    selected_values=selected
                ))
                logger.debug(f"Categorical constraint for {field_name}: {selected}")

        # Collect free-text
        free_text_input = self.query_one("#free-text", Input).value.strip()
        free_text = []
        if free_text_input:
            free_text = [t.strip() for t in free_text_input.split(",") if t.strip()]
            logger.debug(f"Free-text constraints: {free_text}")

        constraints = AnalysisConstraints(
            date_range=date_range,
            categorical=categorical if categorical else [],
            free_text=free_text if free_text else []
        )

        return constraints

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string in YYYY-MM-DD format.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date object or None if invalid
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    def _validate_constraints(self, constraints: AnalysisConstraints) -> Optional[str]:
        """
        Validate constraints and return error message if invalid.

        Args:
            constraints: Constraints to validate

        Returns:
            Error message string if invalid, None if valid
        """
        # Validate date range
        if constraints.date_range:
            # Check if dates were parsed correctly
            start_str = self.query_one("#date-start", Input).value.strip()
            end_str = self.query_one("#date-end", Input).value.strip()

            if start_str and not constraints.date_range.start_date:
                return "시작일 형식이 올바르지 않습니다 (YYYY-MM-DD)"

            if end_str and not constraints.date_range.end_date:
                return "종료일 형식이 올바르지 않습니다 (YYYY-MM-DD)"

            # Validate date range logic
            if not constraints.date_range.validate():
                return "시작일이 종료일보다 늦을 수 없습니다"

        # All validations passed
        return None
