"""Layout Calculator Module
Calculates component positions using a 12-column grid system.
"""
from typing import Dict, Any, List, Optional, Tuple


class LayoutCalculator:
    """
    Manages dashboard layout using a 12-column responsive grid system.
    Automatically positions components to maximize space utilization.
    """

    GRID_COLUMNS = 12
    DEFAULT_MARGIN = 10
    DEFAULT_PADDING = 20

    def __init__(self, grid_columns: int = GRID_COLUMNS):
        """
        Initialize the LayoutCalculator.

        Args:
            grid_columns: Number of columns in the grid (default: 12)
        """
        self.grid_columns = grid_columns
        self.margin = self.DEFAULT_MARGIN
        self.padding = self.DEFAULT_PADDING

    def calculate_layout(
        self,
        components: List[Dict[str, Any]],
        container_width: int = 1200
    ) -> List[Dict[str, Any]]:
        """
        Calculates positions for all components in a grid layout.

        Args:
            components: List of component definitions with layout hints
                       Expected format: [
                           {
                               "id": str,
                               "type": str,
                               "layout": {"width": int, "height": int}
                           },
                           ...
                       ]
            container_width: Total width of the container in pixels

        Returns:
            List of components with calculated positions (x, y, width, height in pixels)
        """
        positioned_components = []
        current_row = 0
        current_col = 0
        row_height = 100  # Default row height in pixels

        column_width = (container_width - (self.margin * (self.grid_columns + 1))) / self.grid_columns

        for component in components:
            layout = component.get("layout", {})
            comp_width = layout.get("width", 12)  # Default to full width
            comp_height = layout.get("height", 1)  # Default to 1 row

            # Check if component fits in current row
            if current_col + comp_width > self.grid_columns:
                # Move to next row
                current_row += 1
                current_col = 0

            # Calculate pixel positions
            x = self.margin + (current_col * (column_width + self.margin))
            y = self.margin + (current_row * (row_height + self.margin))
            width = (comp_width * column_width) + ((comp_width - 1) * self.margin)
            height = (comp_height * row_height) + ((comp_height - 1) * self.margin)

            positioned_component = {
                **component,
                "position": {
                    "x": int(x),
                    "y": int(y),
                    "width": int(width),
                    "height": int(height),
                    "grid_col": current_col,
                    "grid_row": current_row,
                    "grid_width": comp_width,
                    "grid_height": comp_height
                }
            }

            positioned_components.append(positioned_component)

            # Update current position
            current_col += comp_width

        return positioned_components

    def auto_layout(
        self,
        components: List[Dict[str, Any]],
        layout_strategy: str = "balanced"
    ) -> List[Dict[str, Any]]:
        """
        Automatically generates layout hints for components based on strategy.

        Args:
            components: List of component definitions (without layout hints)
            layout_strategy: Strategy for layout generation
                           - "balanced": Distribute components evenly
                           - "priority": Give more space to important components
                           - "compact": Minimize vertical space

        Returns:
            List of components with generated layout hints
        """
        if layout_strategy == "balanced":
            return self._balanced_layout(components)
        elif layout_strategy == "priority":
            return self._priority_layout(components)
        elif layout_strategy == "compact":
            return self._compact_layout(components)
        else:
            return self._balanced_layout(components)

    def _balanced_layout(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Distributes components evenly across the grid.

        Args:
            components: List of component definitions

        Returns:
            Components with balanced layout hints
        """
        component_count = len(components)

        if component_count == 0:
            return []

        # Determine grid distribution
        if component_count == 1:
            width_per_component = 12
        elif component_count == 2:
            width_per_component = 6
        elif component_count == 3:
            width_per_component = 4
        elif component_count == 4:
            width_per_component = 3
        else:
            width_per_component = 4  # Default to 3 columns

        result = []
        for component in components:
            comp_type = component.get("type", "")

            # Adjust height based on component type
            if comp_type in ["BarChart", "LineChart", "ScatterPlot"]:
                height = 3
            elif comp_type == "Label":
                height = 1
            elif comp_type.endswith("Filter"):
                height = 1
            else:
                height = 2

            result.append({
                **component,
                "layout": {
                    "width": width_per_component,
                    "height": height
                }
            })

        return result

    def _priority_layout(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Gives priority components more space.

        Args:
            components: List of component definitions

        Returns:
            Components with priority-based layout hints
        """
        result = []

        for i, component in enumerate(components):
            comp_type = component.get("type", "")

            # First component (usually main chart) gets full width
            if i == 0:
                width = 12
                height = 4
            # Filters get smaller width
            elif comp_type.endswith("Filter"):
                width = 3
                height = 1
            # KPIs get medium width
            elif comp_type == "Label":
                width = 2
                height = 1
            # Other charts get half width
            else:
                width = 6
                height = 3

            result.append({
                **component,
                "layout": {
                    "width": width,
                    "height": height
                }
            })

        return result

    def _compact_layout(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Minimizes vertical space by packing components tightly.

        Args:
            components: List of component definitions

        Returns:
            Components with compact layout hints
        """
        result = []

        for component in components:
            comp_type = component.get("type", "")

            # Small heights for all components
            if comp_type.endswith("Filter"):
                width = 2
                height = 1
            elif comp_type == "Label":
                width = 2
                height = 1
            elif comp_type in ["BarChart", "LineChart"]:
                width = 12
                height = 2
            else:
                width = 6
                height = 2

            result.append({
                **component,
                "layout": {
                    "width": width,
                    "height": height
                }
            })

        return result

    def optimize_layout(
        self,
        components: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Optimizes component layout to reduce empty spaces.

        Args:
            components: List of components with layout hints

        Returns:
            Optimized layout with minimal gaps
        """
        # Sort components by height (descending) for better packing
        sorted_components = sorted(
            components,
            key=lambda c: c.get("layout", {}).get("height", 1),
            reverse=True
        )

        # Use greedy bin-packing algorithm
        rows: List[List[Dict[str, Any]]] = []
        current_row: List[Dict[str, Any]] = []
        current_row_width = 0

        for component in sorted_components:
            comp_width = component.get("layout", {}).get("width", 12)

            if current_row_width + comp_width <= self.grid_columns:
                # Fits in current row
                current_row.append(component)
                current_row_width += comp_width
            else:
                # Start new row
                if current_row:
                    rows.append(current_row)
                current_row = [component]
                current_row_width = comp_width

        # Add last row
        if current_row:
            rows.append(current_row)

        # Flatten back to list
        optimized = []
        for row in rows:
            optimized.extend(row)

        return optimized

    def get_grid_info(self) -> Dict[str, Any]:
        """
        Returns current grid configuration.

        Returns:
            Dictionary with grid settings
        """
        return {
            "grid_columns": self.grid_columns,
            "margin": self.margin,
            "padding": self.padding,
            "default_row_height": 100
        }

    def set_grid_config(
        self,
        grid_columns: Optional[int] = None,
        margin: Optional[int] = None,
        padding: Optional[int] = None
    ) -> None:
        """
        Updates grid configuration.

        Args:
            grid_columns: Number of grid columns
            margin: Margin between components in pixels
            padding: Padding inside components in pixels
        """
        if grid_columns is not None:
            self.grid_columns = grid_columns
        if margin is not None:
            self.margin = margin
        if padding is not None:
            self.padding = padding
