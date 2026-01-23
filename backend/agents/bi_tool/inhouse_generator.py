# InHouseGenerator for interactive BI JSON generation

"""InHouseGenerator builds a BI dashboard JSON compatible with the
`suwon_pop.json` schema. It constructs the `connector`, `datamodel`, and
`report` sections and injects interactive elements (`varList`, `eventList`).
Dynamic queries are rendered using Jinja2 (Nunjucks‑compatible) templates
so that parameters supplied at runtime are substituted into the SQL/DSL.
"""

import json
from typing import Dict, Any, List
from jinja2 import Template
from backend.agents.bi_tool.theme_engine import ThemeEngine


class InHouseGenerator:
    """Core generator for BI dashboard JSON.

    The generator expects a *profile* dictionary containing analysis results
    (e.g., column statistics, suggested KPIs). It produces a JSON structure
    with the following top‑level keys:

    - ``connector`` – data source connection information
    - ``datamodel`` – query definitions (dynamic via Jinja2)
    - ``report`` – layout, visual components, and interactive metadata
    """

    def __init__(self, profile: Dict[str, Any], theme_name: str = "premium_dark"):
        self.profile = profile
        self.theme_engine = ThemeEngine(theme_name)
        # The final JSON will be stored here
        self.dashboard: Dict[str, Any] = {"connector": [], "datamodel": [], "report": []}

    # ---------------------------------------------------------------------
    # Connector builder
    # ---------------------------------------------------------------------
    def build_connector(self, db_type: str = "postgres", host: str = "localhost", port: int = 5432, database: str = "mydb") -> None:
        """Create a connector entry.

        Parameters are simplified for the MVP; in a real system they would be
        derived from configuration or user input.
        """
        connector = {
            "id": "auto-connector",
            "type": db_type,
            "config": {
                "host": host,
                "port": str(port),
                "database": database,
            },
        }
        self.dashboard["connector"].append(connector)

    # ---------------------------------------------------------------------
    # Datamodel builder – includes dynamic query generation
    # ---------------------------------------------------------------------
    def _render_query(self, template_str: str, params: Dict[str, Any]) -> str:
        """Render a Nunjucks‑style query using Jinja2.

        ``template_str`` may contain ``{{ variable }}`` placeholders that are
        replaced by values from ``params``.
        """
        tmpl = Template(template_str)
        return tmpl.render(**params)

    def build_datamodel(self, name: str, base_query: str, param_definitions: Dict[str, Any]) -> None:
        """Create a datamodel entry with a dynamic query.

        ``param_definitions`` maps parameter names to default values. The
        generated JSON stores the raw template and the rendered query (using the
        defaults) so that downstream components can re‑render with user‑supplied
        values.
        """
        # Render the query once with defaults for documentation purposes
        rendered = self._render_query(base_query, param_definitions)
        datamodel = {
            "id": f"dm-{name}",
            "name": name,
            "connector_id": "auto-connector",
            "dataset": {
                "query": base_query,  # keep the template
                "rendered_query": rendered,
                "parameters": param_definitions,
            },
        }
        self.dashboard["datamodel"].append(datamodel)

    # ---------------------------------------------------------------------
    # Report builder – layout + interactive metadata
    # ---------------------------------------------------------------------
    def _default_var(self, name: str, var_type: str = "parameter", default: str = "") -> Dict[str, Any]:
        return {"id": f"var-{name}", "name": name, "type": var_type, "value": default}

    def _default_event(self, from_id: str, to_id: str, event_type: str = "commonDataReceived") -> Dict[str, Any]:
        return {"eventType": event_type, "fromId": from_id, "toId": to_id}

    def build_report(self, title: str, components: List[Dict[str, Any]], var_list: List[Dict[str, Any]] = None, event_list: List[Dict[str, Any]] = None) -> None:
        """Create the ``report`` section.

        ``components`` is a list of visual component definitions.
        If ``var_list`` or ``event_list`` are provided, they are used directly.
        Otherwise, a simple default mapping is created.
        """
        report = {
            "id": "report-1",
            "name": title,
            "visual": [],
        }
        
        # Inject styles into components using ThemeEngine
        styled_components = []
        for comp in components:
            styled_comp = comp.copy()
            styled_comp["style"] = self.theme_engine.get_style(comp["type"])
            styled_components.append(styled_comp)
        
        report["visual"] = styled_components
        
        # Use provided lists or fallback to simple auto-mapping
        if var_list is not None:
            report["varList"] = var_list
        if event_list is not None:
            report["eventList"] = event_list
            
        # Fallback if both are empty (for backward compatibility or simple cases)
        if var_list is None and event_list is None:
            v_list = []
            e_list = []
            for i, comp in enumerate(components):
                comp_id = comp.get("id", f"comp-{i}")
                var = self._default_var(name=comp_id)
                v_list.append(var)
                e_list.append(self._default_event(from_id=var["id"], to_id=comp_id))
            report["varList"] = v_list
            report["eventList"] = e_list

        self.dashboard["report"].append(report)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate(self) -> Dict[str, Any]:
        """Return the assembled dashboard JSON.
        """
        return self.dashboard

    def dump_to_file(self, path: str) -> None:
        """Write the generated JSON to ``path`` with pretty formatting.
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.dashboard, f, ensure_ascii=False, indent=2)

# Example usage (removed from production code, kept for reference)
# if __name__ == "__main__":
#     profile = {}
#     gen = InHouseGenerator(profile)
#     gen.build_connector()
#     gen.build_datamodel(
#         name="population_stats",
#         base_query="SELECT * FROM population WHERE year = {{ year }}",
#         param_definitions={"year": 2022},
#     )
#     gen.build_report(
#         title="인구 통계 대시보드",
#         components=[{"id": "chart-1", "type": "bar", "dataModelId": "dm-population_stats"}],
#     )
#     gen.dump_to_file("generated_dashboard.json")

