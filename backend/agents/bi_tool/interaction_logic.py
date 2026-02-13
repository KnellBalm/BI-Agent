"""Interaction Logic Module
Analyzes data profiling results to suggest variables, events, and dynamic queries.
Supports cross-filtering and interactive dashboard configurations.
"""
from typing import Dict, Any, List, Optional, Set

class InteractionLogic:
    """
    Analyzes profiling data and suggests an interactive dashboard configuration.
    Supports cross-filtering, parameter generation, and dynamic query building.
    """

    def suggest_configuration(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggests parameters (varList), events (eventList), and components.
        """
        columns = profile.get("columns", [])
        
        vars_to_create = []
        events_to_create = []
        visuals = []
        query_parts = []
        
        # 1. Identify Filters (Dimensions)
        for col in columns:
            col_name = col["name"]
            col_type = col["type"]
            
            if col_type == "datetime":
                var_id = f"v_{col_name}"
                vars_to_create.append({
                    "id": var_id,
                    "name": f"Filter: {col_name}",
                    "type": "parameter",
                    "value": col.get("max", "")
                })
                # Visual: Date Picker (simplified as a Filter)
                visuals.append({
                    "id": f"filter_{col_name}",
                    "type": "DateFilter",
                    "config": {"column": col_name, "variable": var_id},
                    "layout": {"width": 3, "height": 1}
                })
                # Identifier quoting applied for col_name
                query_parts.append(f"\"{col_name}\" <= '{{{{ {var_id} }}}}'")

            elif col_type == "categorical" and col["unique"] <= 10:
                var_id = f"v_{col_name}"
                top_val = list(col.get("top_values", {}).keys())[0] if col.get("top_values") else ""
                vars_to_create.append({
                    "id": var_id,
                    "name": f"Select: {col_name}",
                    "type": "parameter",
                    "value": top_val
                })
                visuals.append({
                    "id": f"filter_{col_name}",
                    "type": "SelectFilter",
                    "config": {"column": col_name, "variable": var_id},
                    "layout": {"width": 3, "height": 1}
                })
                # Identifier quoting applied for col_name
                query_parts.append(f"\"{col_name}\" = '{{{{ {var_id} }}}}'")

        # 2. Identify KPIs (Measures)
        kpis = [col for col in columns if col["type"] == "numerical"]
        for kpi in kpis[:2]: # Suggest top 2 KPIs
            visuals.append({
                "id": f"kpi_{kpi['name']}",
                "type": "Label",
                "config": {"measure": kpi["name"], "agg": "sum"},
                "layout": {"width": 2, "height": 1}
            })

        # 3. Main Chart (Relation)
        # Find first categorical as X and first numerical as Y
        cat_cols = [col for col in columns if col["type"] == "categorical"]
        if cat_cols and kpis:
            visuals.append({
                "id": "main_chart",
                "type": "BarChart",
                "config": {
                    "dimension": cat_cols[0]["name"],
                    "measure": kpis[0]["name"],
                    "agg": "sum"
                },
                "layout": {"width": 12, "height": 4}
            })

        # 4. Build Dynamic Query
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        base_query = f"SELECT * FROM dataset WHERE {where_clause}"

        return {
            "varList": vars_to_create,
            "eventList": events_to_create, # Automated by InHouseGenerator usually
            "visuals": visuals,
            "dynamic_query": base_query,
            "params": {v["id"]: v["value"] for v in vars_to_create}
        }

    def create_cross_filter_events(
        self,
        visuals: List[Dict[str, Any]],
        profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Creates cross-filtering event configurations between visuals.

        Args:
            visuals: List of visual components
            profile: Data profiling results

        Returns:
            List of event configurations for cross-filtering
        """
        events = []
        chart_visuals = [
            v for v in visuals
            if v.get("type") in ["BarChart", "LineChart", "PieChart", "ScatterPlot"]
        ]

        # Create click events for each chart that can act as a filter
        for visual in chart_visuals:
            config = visual.get("config", {})
            dimension = config.get("dimension") or config.get("category") or config.get("x_axis")

            if dimension:
                # Find target visuals (all other charts using the same dimension)
                target_visuals = [
                    v["id"] for v in chart_visuals
                    if v["id"] != visual["id"]
                ]

                if target_visuals:
                    event = {
                        "eventCode": f"cross_filter_{visual['id']}",
                        "eventType": "click",
                        "sourceVisual": visual["id"],
                        "targetVisuals": target_visuals,
                        "action": "cross_filter",
                        "filterColumn": dimension,
                        "filterValue": "{{clickedValue}}",  # Placeholder
                        "enabled": True
                    }
                    events.append(event)

        return events

    def build_cross_filter_query(
        self,
        base_query: str,
        active_filters: Dict[str, Any]
    ) -> str:
        """
        Builds a query with cross-filter conditions applied.

        Args:
            base_query: Original SQL query
            active_filters: Dictionary of active filters {column: value}

        Returns:
            Modified query with cross-filter WHERE clauses
        """
        if not active_filters:
            return base_query

        filter_clauses = []
        for column, value in active_filters.items():
            if isinstance(value, list):
                # IN clause for multiple values
                values_str = ", ".join([f"'{v}'" for v in value])
                filter_clauses.append(f'"{column}" IN ({values_str})')
            else:
                # Single value equality
                filter_clauses.append(f'"{column}" = \'{value}\'')

        if not filter_clauses:
            return base_query

        combined_filters = " AND ".join(filter_clauses)

        # Insert filters into query
        if "WHERE" in base_query.upper():
            modified_query = base_query.replace(
                "WHERE",
                f"WHERE {combined_filters} AND"
            )
        else:
            # Add WHERE clause before GROUP BY or at the end
            if "GROUP BY" in base_query.upper():
                modified_query = base_query.replace(
                    "GROUP BY",
                    f"WHERE {combined_filters} GROUP BY"
                )
            else:
                modified_query = f"{base_query} WHERE {combined_filters}"

        return modified_query

    def get_affected_visuals(
        self,
        event: Dict[str, Any],
        all_visuals: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Determines which visuals are affected by a cross-filter event.

        Args:
            event: Event configuration
            all_visuals: List of all visual components

        Returns:
            List of affected visual IDs
        """
        if event.get("action") != "cross_filter":
            return []

        # Direct targets specified in event
        target_visuals = event.get("targetVisuals", [])

        if target_visuals:
            return target_visuals

        # Otherwise, affect all visuals except source
        source_id = event.get("sourceVisual")
        return [
            v["id"] for v in all_visuals
            if v["id"] != source_id
        ]

    def create_bidirectional_filters(
        self,
        visual_a_id: str,
        visual_b_id: str,
        shared_dimension: str
    ) -> List[Dict[str, Any]]:
        """
        Creates bidirectional cross-filter events between two visuals.

        Args:
            visual_a_id: First visual ID
            visual_b_id: Second visual ID
            shared_dimension: Column name shared by both visuals

        Returns:
            List of two event configurations (A→B and B→A)
        """
        events = []

        # Event A → B
        events.append({
            "eventCode": f"cross_filter_{visual_a_id}_to_{visual_b_id}",
            "eventType": "click",
            "sourceVisual": visual_a_id,
            "targetVisuals": [visual_b_id],
            "action": "cross_filter",
            "filterColumn": shared_dimension,
            "filterValue": "{{clickedValue}}",
            "bidirectional": True,
            "enabled": True
        })

        # Event B → A
        events.append({
            "eventCode": f"cross_filter_{visual_b_id}_to_{visual_a_id}",
            "eventType": "click",
            "sourceVisual": visual_b_id,
            "targetVisuals": [visual_a_id],
            "action": "cross_filter",
            "filterColumn": shared_dimension,
            "filterValue": "{{clickedValue}}",
            "bidirectional": True,
            "enabled": True
        })

        return events

    def detect_shared_dimensions(
        self,
        visuals: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Detects which dimensions are shared across multiple visuals.

        Args:
            visuals: List of visual components

        Returns:
            Dictionary mapping dimension names to lists of visual IDs using them
        """
        dimension_map: Dict[str, List[str]] = {}

        for visual in visuals:
            config = visual.get("config", {})
            dimensions = []

            # Extract all dimension-like fields
            if "dimension" in config:
                dimensions.append(config["dimension"])
            if "category" in config:
                dimensions.append(config["category"])
            if "x_axis" in config:
                dimensions.append(config["x_axis"])
            if "hierarchy" in config:
                if isinstance(config["hierarchy"], list):
                    dimensions.extend(config["hierarchy"])

            # Map dimensions to visuals
            for dim in dimensions:
                if dim:
                    if dim not in dimension_map:
                        dimension_map[dim] = []
                    dimension_map[dim].append(visual["id"])

        # Filter to only shared dimensions (used by 2+ visuals)
        shared = {
            dim: visuals_list
            for dim, visuals_list in dimension_map.items()
            if len(visuals_list) >= 2
        }

        return shared

    def create_filter_state(
        self,
        active_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a filter state object to track active cross-filters.

        Args:
            active_filters: Initial filters {column: value}

        Returns:
            Filter state object
        """
        return {
            "active_filters": active_filters or {},
            "filter_history": [],
            "locked_filters": []
        }

    def apply_filter(
        self,
        filter_state: Dict[str, Any],
        column: str,
        value: Any,
        add_to_history: bool = True
    ) -> Dict[str, Any]:
        """
        Applies a filter to the current state.

        Args:
            filter_state: Current filter state
            column: Column to filter on
            value: Filter value
            add_to_history: Whether to add to history for undo

        Returns:
            Updated filter state
        """
        if add_to_history:
            # Save current state to history
            filter_state["filter_history"].append(
                dict(filter_state["active_filters"])
            )

        # Apply new filter
        filter_state["active_filters"][column] = value

        return filter_state

    def clear_filter(
        self,
        filter_state: Dict[str, Any],
        column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clears filters from the state.

        Args:
            filter_state: Current filter state
            column: Specific column to clear (None = clear all)

        Returns:
            Updated filter state
        """
        if column:
            if column in filter_state["active_filters"]:
                del filter_state["active_filters"][column]
        else:
            # Clear all non-locked filters
            locked = filter_state.get("locked_filters", set())
            filter_state["active_filters"] = {
                k: v for k, v in filter_state["active_filters"].items()
                if k in locked
            }

        return filter_state
