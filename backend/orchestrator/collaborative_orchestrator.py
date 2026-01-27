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
from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider
from backend.utils.dashboard_generator import DashboardGenerator
from backend.utils.output_packager import OutputPackager
from backend.utils.path_config import path_manager

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
        
        # Initialize LLM for Coaching & Insights
        primary = GeminiProvider()
        secondary = OllamaProvider()
        self.llm = FailoverLLMProvider(primary, secondary)
        
        # Local Dashboard Generator & Packager
        self.dash_gen = DashboardGenerator(project_id)
        self.packager = OutputPackager(project_id)

    async def run(self, query: str, conn_id: str) -> Dict[str, Any]:
        """
        Entrance Hall 등에서 호출하는 메인 진입점입니다.
        """
        return await self.handle_complex_request(query, conn_id)

    async def handle_complex_request(self, user_query: str, conn_id: str) -> Dict[str, Any]:

        try:
            # --- [Step 1: DataMaster] Context Discovery ---
            try:
                meta = self.scanner.scan_source(conn_id)
                is_simulation = False
            except Exception as e:
                print(f"⚠️ Connection failed for {conn_id}: {e}. Triggering Plan B: Virtual Schema.")
                meta = await self._handle_connection_failure(user_query)
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
            output_path = path_manager.get_output_path(conn_id) / f"collaborative_data{suffix}.json"
            generator.dump_to_file(str(output_path))
            
            result = {
                "status": "success",
                "is_simulation": is_simulation,
                "path": output_path,
                "reasoning": strategy["reasoning"],
                "summary": {
                    "table": target_table["table_name"],
                    "visuals": [v["type"] for v in config["visuals"]],
                    "parameters": list(config["params"].keys())
                },
                "proactive_questions": await self._generate_proactive_questions(user_query, target_table)
            }
            
            # Generate Web Dashboard
            dash_path = self.dash_gen.generate_dashboard(result)
            result["dashboard_url"] = dash_path
            self.dash_gen.open_in_browser(dash_path)
            
            return result
        except Exception as e:
            return {"status": "error", "message": f"Orchestration failed: {str(e)}"}

    async def handle_user_sql(self, sql_query: str, conn_id: str) -> Dict[str, Any]:
        """
        Processes a user-submitted SQL query with AI coaching.
        """
        print(f"👨‍💻 Processing user SQL: {sql_query}")
        try:
            # 1. AI Coaching: Refine and Comment
            coaching_result = await self._get_sql_coaching(sql_query, conn_id)
            refined_sql = coaching_result.get("refined_sql", sql_query)
            
            # 2. Execute Query
            df = self.conn_mgr.run_query(conn_id, refined_sql)
            
            # 3. Basic analysis of result
            row_count = len(df)
            columns = df.columns.tolist()
            
            result = {
                "status": "success",
                "sql_used": refined_sql,
                "coaching": coaching_result.get("advice", "Query looks good!"),
                "result_summary": f"Executed successfully. Returned {row_count} rows with columns: {', '.join(columns)}",
                "data_preview": df.head(5).to_dict(orient="records"),
                "summary": {"table": f"SQL Result ({conn_id})", "visuals": ["DataTable"]},
                "proactive_questions": await self._generate_proactive_questions(f"SQL: {sql_query}", {"table_name": "custom_query", "columns": []})
            }
            
            # Generate Web Dashboard
            dash_path = self.dash_gen.generate_dashboard(result)
            result["dashboard_url"] = dash_path
            self.dash_gen.open_in_browser(dash_path)
            
            return result
        except Exception as e:
            return {"status": "error", "message": f"SQL Execution/Coaching failed: {str(e)}"}

    async def _get_sql_coaching(self, sql: str, conn_id: str) -> Dict[str, Any]:
        """Uses LLM to provide feedback and refined version of user SQL."""
        try:
            meta = self.scanner.scan_source(conn_id)
            schema_context = json.dumps(meta.get("tables", []), indent=2)
            
            prompt = f"""
            You are an expert BI SQL Coach. A user submitted the following SQL query:
            ---
            {sql}
            ---
            Database Schema Context:
            {schema_context}
            
            Task:
            1. Validate the syntax and column names against the schema.
            2. Suggest performance optimizations (e.g., joins, filters).
            3. Add business context comments to the query.
            4. If the query is likely incorrect, provide a corrected version.
            
            Return ONLY a valid JSON object with keys:
            - "refined_sql": The updated SQL string.
            - "advice": A short snippet of advice or praise for the user (in Korean).
            """
            response = await self.llm.generate(prompt)
            # Find JSON block
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"refined_sql": sql, "advice": "도움말을 생성하지 못했습니다."}
        except:
            return {"refined_sql": sql, "advice": "쿼리를 실행합니다. (코칭 기능을 불러오는 중 오류 발생)"}

    async def _handle_connection_failure(self, query: str) -> Dict[str, Any]:
        """
        Plan B: Infers a virtual schema based on the user's intent when connection fails.
        """
        try:
            prompt = f"""
            The user wants to analyze data but the database connection failed.
            Request: "{query}"
            
            Task:
            Infer a likely database schema (table name and columns) that would be needed to answer this request.
            Return a JSON object matching the MetadataScanner output format:
            {{
                "tables": [
                    {{
                        "table_name": "inferred_table_name",
                        "row_count_estimate": 1000,
                        "columns": [
                            {{"name": "col_name", "type": "categorical|numerical|temporal", "semantic": "measure|dimension"}}
                        ]
                    }}
                ]
            }}
            """
            response = await self.llm.generate(prompt)
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        return self._get_simulation_metadata()

    async def _generate_proactive_questions(self, query: str, table_meta: Dict[str, Any]) -> List[str]:
        """Generates follow-up analysis questions based on context."""
        try:
            prompt = f"""
            Based on the analysis request: "{query}"
            Data Schema: {json.dumps(table_meta, indent=2)}
            
            Task:
            Generate 3 strategic deep-dive suggestions. For each, use the format:
            "**[가설]** ... **[질문]** ... **[기대효과]** ..."
            
            Requirements:
            - Focus on business growth, risk mitigation, or operational efficiency.
            - Use professional yet approachable Korean.
            - Return as a simple list of strings.
            """
            response = await self.llm.generate(prompt)
            # Simple parsing for list
            questions = [q.strip("- ").strip("123. ") for q in response.split("\n") if len(q.strip()) > 10]
            return questions[:3]
        except:
            return ["추가 인사이트를 탐색해보세요."]

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
