"""Drilldown Mapper Module
Automatically detects hierarchical relationships in data and creates drilldown paths.
"""
from typing import Dict, Any, List, Optional, Tuple


class DrilldownMapper:
    """
    Detects and manages drilldown hierarchies in dimensional data.
    Supports automatic hierarchy detection based on cardinality and naming patterns.
    """

    # Common hierarchy patterns (column name patterns)
    HIERARCHY_PATTERNS = {
        "time": ["year", "quarter", "month", "week", "day", "hour"],
        "geography": ["country", "region", "state", "city", "district", "postal_code"],
        "organization": ["company", "department", "team", "employee"],
        "product": ["category", "subcategory", "brand", "product", "sku"],
        "customer": ["segment", "tier", "customer_type", "customer"]
    }

    def __init__(self):
        """Initialize the DrilldownMapper."""
        pass

    def detect_hierarchies(
        self,
        profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Automatically detects hierarchical relationships in the data.

        Args:
            profile: Data profiling results containing column metadata
                    Expected format: {
                        "columns": [
                            {"name": str, "type": str, "unique": int, ...},
                            ...
                        ]
                    }

        Returns:
            List of detected hierarchies:
            [
                {
                    "name": str,
                    "type": str,
                    "levels": [str, ...],
                    "cardinalities": [int, ...]
                },
                ...
            ]
        """
        columns = profile.get("columns", [])
        categorical_cols = [
            col for col in columns
            if col.get("type") == "categorical"
        ]

        hierarchies = []

        # 1. Pattern-based detection
        pattern_hierarchies = self._detect_by_pattern(categorical_cols)
        hierarchies.extend(pattern_hierarchies)

        # 2. Cardinality-based detection
        cardinality_hierarchies = self._detect_by_cardinality(categorical_cols)
        hierarchies.extend(cardinality_hierarchies)

        # 3. Remove duplicates
        hierarchies = self._deduplicate_hierarchies(hierarchies)

        return hierarchies

    def create_drilldown_path(
        self,
        hierarchy: Dict[str, Any],
        start_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a drilldown path configuration for a hierarchy.

        Args:
            hierarchy: Hierarchy definition from detect_hierarchies()
            start_level: Starting level (defaults to first level)

        Returns:
            Drilldown path configuration:
            {
                "hierarchy_name": str,
                "path": [
                    {"level": str, "column": str},
                    ...
                ],
                "current_level": str,
                "can_drill_down": bool,
                "can_drill_up": bool
            }
        """
        levels = hierarchy.get("levels", [])

        if not levels:
            return {
                "hierarchy_name": hierarchy.get("name", "unknown"),
                "path": [],
                "current_level": None,
                "can_drill_down": False,
                "can_drill_up": False
            }

        # Determine starting level
        if start_level and start_level in levels:
            current_idx = levels.index(start_level)
        else:
            current_idx = 0

        current_level = levels[current_idx]

        # Build path
        path = [
            {"level": i + 1, "column": level}
            for i, level in enumerate(levels)
        ]

        return {
            "hierarchy_name": hierarchy.get("name", "unknown"),
            "path": path,
            "current_level": current_level,
            "current_level_index": current_idx,
            "can_drill_down": current_idx < len(levels) - 1,
            "can_drill_up": current_idx > 0,
            "next_level": levels[current_idx + 1] if current_idx < len(levels) - 1 else None,
            "prev_level": levels[current_idx - 1] if current_idx > 0 else None
        }

    def generate_drilldown_query(
        self,
        base_query: str,
        drilldown_path: Dict[str, Any],
        drill_action: str = "down",
        filter_value: Optional[str] = None
    ) -> str:
        """
        Generates SQL query for drilldown navigation.

        Args:
            base_query: Original SQL query
            drilldown_path: Path configuration from create_drilldown_path()
            drill_action: "down" or "up"
            filter_value: Value to filter on when drilling down

        Returns:
            Modified SQL query for drilldown
        """
        current_level = drilldown_path.get("current_level")
        next_level = drilldown_path.get("next_level")
        prev_level = drilldown_path.get("prev_level")

        if drill_action == "down" and next_level:
            # Drill down: add filter on current level, group by next level
            if filter_value:
                filter_clause = f'"{current_level}" = \'{filter_value}\''

                # Simple query modification (assumes SELECT ... FROM ... structure)
                if "WHERE" in base_query.upper():
                    modified_query = base_query.replace(
                        "WHERE",
                        f"WHERE {filter_clause} AND"
                    )
                else:
                    # Add WHERE clause before GROUP BY or ORDER BY
                    if "GROUP BY" in base_query.upper():
                        modified_query = base_query.replace(
                            "GROUP BY",
                            f"WHERE {filter_clause} GROUP BY"
                        )
                    else:
                        modified_query = f"{base_query} WHERE {filter_clause}"

                # Update GROUP BY to use next level
                modified_query = modified_query.replace(
                    f'"{current_level}"',
                    f'"{next_level}"'
                )

                return modified_query

        elif drill_action == "up" and prev_level:
            # Drill up: remove deepest filter, group by previous level
            modified_query = base_query.replace(
                f'"{current_level}"',
                f'"{prev_level}"'
            )
            return modified_query

        return base_query

    def create_drilldown_event(
        self,
        visual_id: str,
        hierarchy: Dict[str, Any],
        drilldown_path: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates an event configuration for drilldown interaction.

        Args:
            visual_id: ID of the visual component
            hierarchy: Hierarchy definition
            drilldown_path: Drilldown path configuration

        Returns:
            Event configuration object for eventList
        """
        current_level = drilldown_path.get("current_level")
        next_level = drilldown_path.get("next_level")

        event = {
            "eventCode": f"drilldown_{visual_id}",
            "eventType": "click",
            "sourceVisual": visual_id,
            "action": "drilldown",
            "hierarchy": hierarchy.get("name"),
            "currentLevel": current_level,
            "nextLevel": next_level,
            "enabled": drilldown_path.get("can_drill_down", False)
        }

        return event

    def _detect_by_pattern(
        self,
        columns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detects hierarchies based on naming patterns.

        Args:
            columns: List of categorical columns

        Returns:
            List of detected hierarchies
        """
        hierarchies = []

        for hierarchy_type, pattern_levels in self.HIERARCHY_PATTERNS.items():
            matched_columns = []

            for level in pattern_levels:
                # Find columns that contain the level name
                matching_cols = [
                    col for col in columns
                    if level.lower() in col["name"].lower()
                ]

                if matching_cols:
                    # Use the first match
                    matched_columns.append(matching_cols[0])

            # If we found at least 2 levels, create a hierarchy
            if len(matched_columns) >= 2:
                hierarchies.append({
                    "name": hierarchy_type,
                    "type": "pattern",
                    "levels": [col["name"] for col in matched_columns],
                    "cardinalities": [col.get("unique", 0) for col in matched_columns]
                })

        return hierarchies

    def _detect_by_cardinality(
        self,
        columns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detects hierarchies based on cardinality relationships.

        Args:
            columns: List of categorical columns

        Returns:
            List of detected hierarchies
        """
        hierarchies = []

        # Sort columns by cardinality (ascending)
        sorted_cols = sorted(
            columns,
            key=lambda c: c.get("unique", 0)
        )

        # Group columns with increasing cardinality
        hierarchy_candidates = []
        current_group = []

        for i, col in enumerate(sorted_cols):
            if not current_group:
                current_group.append(col)
            else:
                prev_cardinality = current_group[-1].get("unique", 0)
                curr_cardinality = col.get("unique", 0)

                # If cardinality increases by at least 2x, consider it next level
                if curr_cardinality >= prev_cardinality * 2:
                    current_group.append(col)
                else:
                    # Save current group if it has at least 2 levels
                    if len(current_group) >= 2:
                        hierarchy_candidates.append(current_group)
                    current_group = [col]

        # Don't forget the last group
        if len(current_group) >= 2:
            hierarchy_candidates.append(current_group)

        # Convert to hierarchy format
        for idx, group in enumerate(hierarchy_candidates):
            hierarchies.append({
                "name": f"hierarchy_{idx + 1}",
                "type": "cardinality",
                "levels": [col["name"] for col in group],
                "cardinalities": [col.get("unique", 0) for col in group]
            })

        return hierarchies

    def _deduplicate_hierarchies(
        self,
        hierarchies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Removes duplicate hierarchies based on overlapping levels.

        Args:
            hierarchies: List of detected hierarchies

        Returns:
            Deduplicated list
        """
        if not hierarchies:
            return []

        unique = []

        for hierarchy in hierarchies:
            levels_set = set(hierarchy["levels"])

            # Check if this hierarchy overlaps significantly with existing ones
            is_duplicate = False
            for existing in unique:
                existing_levels = set(existing["levels"])

                # If more than 50% overlap, consider duplicate
                overlap = len(levels_set & existing_levels)
                if overlap / len(levels_set) > 0.5:
                    is_duplicate = True

                    # Keep the longer hierarchy
                    if len(hierarchy["levels"]) > len(existing["levels"]):
                        unique.remove(existing)
                        unique.append(hierarchy)
                    break

            if not is_duplicate:
                unique.append(hierarchy)

        return unique

    def get_drilldown_breadcrumb(
        self,
        drilldown_path: Dict[str, Any],
        filters: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """
        Generates breadcrumb navigation for current drilldown state.

        Args:
            drilldown_path: Drilldown path configuration
            filters: Current filter values {level: value}

        Returns:
            Breadcrumb items:
            [
                {"level": str, "value": str, "clickable": bool},
                ...
            ]
        """
        path = drilldown_path.get("path", [])
        current_idx = drilldown_path.get("current_level_index", 0)

        breadcrumbs = []

        for i in range(current_idx + 1):
            level_info = path[i]
            column_name = level_info["column"]
            value = filters.get(column_name, "All")

            breadcrumbs.append({
                "level": column_name,
                "value": value,
                "clickable": i < current_idx  # Can drill back up
            })

        return breadcrumbs
