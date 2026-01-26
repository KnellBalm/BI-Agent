"""
Collaborative Orchestrator Module
Coordinates specialized skills (Strategist, Designer, DataMaster) to handle
complex BI requests and generate premium dashboards.
"""
from typing import Dict, Any, List, Optional
import json
from backend.agents.bi_tool.inhouse_generator import InHouseGenerator
from backend.agents.bi_tool.interaction_logic import InteractionLogic
from backend.agents.data_source.connection_manager import ConnectionManager
from backend.agents.data_source.metadata_scanner import MetadataScanner

from backend.agents.bi_tool.metric_store import MetricStore

class CollaborativeOrchestrator:
    """
    Advanced orchestrator that implements a multi-agent collaboration flow.
    """

    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.conn_mgr = ConnectionManager(project_id)
        self.scanner = MetadataScanner(self.conn_mgr)
        self.metric_store = MetricStore(project_id)
        self.logic = InteractionLogic()

    async def handle_complex_request(self, user_query: str, conn_id: str) -> Dict[str, Any]:
        """
        Executes a full collaborative loop with simulation fallback.
        """
        print(f"🧠 Processing complex query: {user_query}")

        try:
            # --- [Step 1: DataMaster] Context Discovery ---
            try:
                meta = self.scanner.scan_source(conn_id)
                is_simulation = False
            except Exception as e:
                print(f"⚠️ Connection failed for {conn_id}: {e}. Switching to Simulation Mode.")
                meta = self._get_simulation_metadata()
                is_simulation = True

            if not meta["tables"]:
                return {"status": "error", "message": "No tables found in data source."}
            
            # Pick the most relevant table (Simplified)
            target_table = meta["tables"][0]
            table_name = target_table['table_name']
            sim_prefix = "[SIMULATION] " if is_simulation else ""
            print(f"🔍 [DataMaster] {sim_prefix}Selected table: {table_name}")

            # --- [Step 2: Strategist] Goal Definition (Metric Aware) ---
            active_metrics = self.metric_store.get_metrics_for_table(table_name)
            metric_context = ""
            if active_metrics:
                metric_names = [m["id"] for m in active_metrics]
                metric_context = f" [Metrics: {', '.join(metric_names)}]"
            
            strategy = {
                "goal": "Performance Analysis",
                "focus_columns": [c["name"] for c in target_table["columns"]],
                "active_metrics": active_metrics,
                "reasoning": f"{sim_prefix}Found schema for {user_query}.{metric_context} Proceeding with analysis."
            }
            print(f"🎯 [Strategist] Plan: {strategy['reasoning']}")
 
            # --- [Step 3: VisualDesigner] Composition ---
            profile = {
                "columns": target_table["columns"],
                "overview": {"rows": target_table["row_count_estimate"]},
                "metrics": active_metrics
            }
            config = self.logic.suggest_configuration(profile)
            print(f"🎨 [Designer] Suggested {len(config['visuals'])} visuals.")

            # --- [Step 4: Generation] Assembly ---
            generator = InHouseGenerator(profile, theme_name="premium_dark")
            generator.build_connector()
            
            generator.build_datamodel(
                name=f"dm_{target_table['table_name']}",
                base_query=config["dynamic_query"],
                param_definitions=config["params"]
            )
            
            generator.build_report(
                title=f"{sim_prefix}{target_table['table_name'].capitalize()} Insights",
                components=config["visuals"],
                var_list=config["varList"],
                event_list=config["eventList"]
            )

            suffix = "_sim" if is_simulation else ""
            output_path = f"/tmp/collaborative_{conn_id}{suffix}.json"
            generator.dump_to_file(output_path)
            
            return {
                "status": "success",
                "is_simulation": is_simulation,
                "path": output_path,
                "reasoning": strategy["reasoning"],
                "summary": {
                    "table": target_table["table_name"],
                    "visuals": [v["type"] for v in config["visuals"]],
                    "parameters": list(config["params"].keys())
                }
            }
        except Exception as e:
            return {"status": "error", "message": f"Orchestration failed: {str(e)}"}

    def _get_simulation_metadata(self) -> Dict[str, Any]:
        """Provides a generic high-quality mock schema for simulation mode."""
        return {
            "tables": [
                {
                    "table_name": "mock_global_sales",
                    "row_count_estimate": 15000,
                    "columns": [
                        {"name": "order_date", "type": "DATE", "semantic": "temporal"},
                        {"name": "region", "type": "TEXT", "semantic": "spatial"},
                        {"name": "category", "type": "TEXT", "semantic": "categorical"},
                        {"name": "sales_amount", "type": "REAL", "semantic": "measure"},
                        {"name": "profit", "type": "REAL", "semantic": "measure"},
                        {"name": "quantity", "type": "INTEGER", "semantic": "measure"}
                    ]
                }
            ]
        }

if __name__ == "__main__":
    # Test with mockup
    orchestrator = CollaborativeOrchestrator("/tmp/collab_test.json")
    orchestrator.conn_mgr.register_connection("test_db", "sqlite", {"path": ":memory:"})
    
    # Setup mock data via DataMaster-like direct access for setup
    conn = orchestrator.conn_mgr.get_connection("test_db")
    conn.execute("CREATE TABLE sales (region TEXT, amount REAL, report_date TEXT)")
    conn.execute("INSERT INTO sales VALUES ('Seoul', 5000, '2023-01-01'), ('Busan', 3000, '2023-01-01')")
    conn.commit()
    
    result = orchestrator.handle_complex_request("Show me regional sales performance", "test_db")
    print(json.dumps(result, indent=2))
    
    import os
    os.remove("/tmp/collab_test.json")
