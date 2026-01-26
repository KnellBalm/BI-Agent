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

class CollaborativeOrchestrator:
    """
    Advanced orchestrator that implements a multi-agent collaboration flow.
    """

    def __init__(self, connection_registry: str = "config/connections.json"):
        self.conn_mgr = ConnectionManager(connection_registry)
        self.scanner = MetadataScanner(self.conn_mgr)
        self.logic = InteractionLogic()

    def handle_complex_request(self, user_query: str, conn_id: str) -> Dict[str, Any]:
        """
        Executes a full collaborative loop:
        1. Context Discovery (DataMaster Role)
        2. Insight Strategy (Strategist Role)
        3. Visual Composition (Designer Role)
        4. Generation & Theming
        """
        print(f"🧠 Processing complex query: {user_query}")

        # --- [Step 1: DataMaster] Context Discovery ---
        # List tables and pick the most relevant one (simulated strategist decision)
        meta = self.scanner.scan_source(conn_id)
        if not meta["tables"]:
            return {"status": "error", "message": "No tables found in data source."}
        
        # Pick the first table for now (In real case, Strategist would decide based on query)
        target_table = meta["tables"][0]
        print(f"🔍 [DataMaster] Selected table: {target_table['table_name']}")

        # --- [Step 2: Strategist] Goal Definition ---
        # Analyze user query to define parameters (Simulated)
        # e.g., 'Compare sales by region' -> Strategist identifies 'sales' as measure, 'region' as dimension
        strategy = {
            "goal": "Performance Analysis",
            "focus_columns": [c["name"] for c in target_table["columns"]],
            "reasoning": f"Analyzing {user_query} using schema provided by DataMaster."
        }
        print(f"🎯 [Strategist] Plan: {strategy['reasoning']}")

        # --- [Step 3: VisualDesigner] Composition ---
        # Suggest config based on profile (Using existing InteractionLogic as core designer)
        # Create a mock profile from target_table for the logic
        profile = {
            "columns": target_table["columns"],
            "overview": {"rows": target_table["row_count_estimate"]}
        }
        config = self.logic.suggest_configuration(profile)
        print(f"🎨 [Designer] Suggested {len(config['visuals'])} visuals with Premium Dark theme.")

        # --- [Step 4: Generation] Assembly ---
        generator = InHouseGenerator(profile, theme_name="premium_dark")
        generator.build_connector()
        
        generator.build_datamodel(
            name=f"dm_{target_table['table_name']}",
            base_query=config["dynamic_query"],
            param_definitions=config["params"]
        )
        
        generator.build_report(
            title=f"{target_table['table_name'].capitalize()} Insights",
            components=config["visuals"],
            var_list=config["varList"],
            event_list=config["eventList"]
        )

        output_path = f"/tmp/collaborative_{conn_id}.json"
        generator.dump_to_file(output_path)
        
        return {
            "status": "success",
            "path": output_path,
            "reasoning": strategy["reasoning"],
            "summary": {
                "table": target_table["table_name"],
                "visuals": [v["type"] for v in config["visuals"]],
                "parameters": list(config["params"].keys())
            }
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
