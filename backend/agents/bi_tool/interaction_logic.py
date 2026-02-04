"""Interaction Logic Module
Analyzes data profiling results to suggest variables, events, and dynamic queries.
"""
from typing import Dict, Any, List

class InteractionLogic:
    """
    Analyzes profiling data and suggests an interactive dashboard configuration.
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
